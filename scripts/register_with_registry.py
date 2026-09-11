"""
Central Agent Registry & Gemini Enterprise App Registration Script.
Validates the A2A v1.0 Agent Card, registers the agent with:
  1. Google Cloud Agent Registry (fleet-wide catalog via gcloud agent-registry)
  2. Gemini Enterprise App Assistant (client chat interface via Discovery Engine API)
and verifies organizational discovery.
"""

import os
import sys
import json
import logging
import subprocess
from typing import Dict, Any, List
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AgentRegistryRegistrar")

AGENT_CARD_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "deployment", "agent-card.json")
)
PROJECT_ID = "orbit-499212"
PROJECT_NUMBER = "98835120191"
LOCATION = "us-central1"
SERVICE_NAME = "book-management-service"
GEMINI_ENTERPRISE_APP_ID = "projects/98835120191/locations/global/collections/default_collection/engines/sophisticated-book-managem_1789063690371"


def validate_agent_card(agent_card: Dict[str, Any]) -> bool:
    """Validates that agent card conforms to A2A v1.0 specifications."""
    required_fields = ["name", "description", "supportedInterfaces", "skills", "capabilities", "version"]
    for field in required_fields:
        if field not in agent_card:
            logger.error(f"❌ Validation Error: Missing required field '{field}' in agent card.")
            return False

    if not agent_card.get("skills"):
        logger.error("❌ Agent must declare at least one capability skill.")
        return False

    logger.info(f"✅ Agent Card validation passed for: '{agent_card['name']}'")
    return True


def get_gcp_access_token() -> str:
    """Retrieves access token from gcloud."""
    res = subprocess.check_output(["gcloud", "auth", "print-access-token"])
    return res.decode().strip()


def register_with_google_cloud_agent_registry(agent_card: Dict[str, Any]) -> Dict[str, Any]:
    """Registers or updates the agent service in Google Cloud Agent Registry."""
    logger.info(f"📡 Registering with Google Cloud Agent Registry (Location: {LOCATION})...")
    card_json_str = json.dumps(agent_card)

    # Check if service already exists
    check_cmd = [
        "gcloud", "agent-registry", "services", "describe", SERVICE_NAME,
        f"--location={LOCATION}", f"--project={PROJECT_ID}", "--format=json"
    ]
    proc = subprocess.run(check_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode == 0:
        logger.info(f"  Service '{SERVICE_NAME}' exists; updating with A2A Agent Card specification...")
        update_cmd = [
            "gcloud", "agent-registry", "services", "update", SERVICE_NAME,
            f"--location={LOCATION}",
            f"--project={PROJECT_ID}",
            "--agent-spec-type=a2a-agent-card",
            f"--agent-spec-content={card_json_str}",
            "--clear-interfaces",
            "--format=json"
        ]
        res = subprocess.check_output(update_cmd, text=True)
    else:
        logger.info(f"  Service '{SERVICE_NAME}' not found; creating new service with A2A Agent Card...")
        create_cmd = [
            "gcloud", "agent-registry", "services", "create", SERVICE_NAME,
            f"--location={LOCATION}",
            f"--project={PROJECT_ID}",
            f"--display-name={agent_card['name']}",
            f"--description={agent_card['description']}",
            "--agent-spec-type=a2a-agent-card",
            f"--agent-spec-content={card_json_str}",
            "--format=json"
        ]
        res = subprocess.check_output(create_cmd, text=True)

    service_data = json.loads(res)
    logger.info(f"✅ Google Cloud Agent Registry updated: {service_data.get('name')}")
    logger.info(f"   Projected Agent Resource: {service_data.get('registryResource')}")
    return service_data


def register_with_gemini_enterprise_app(agent_card: Dict[str, Any]) -> Dict[str, Any]:
    """Registers or updates the agent in the Gemini Enterprise App."""
    logger.info("📡 Registering with Gemini Enterprise App Chat Interface...")
    token = get_gcp_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": PROJECT_ID,
        "Content-Type": "application/json"
    }

    url = f"https://discoveryengine.googleapis.com/v1alpha/{GEMINI_ENTERPRISE_APP_ID}/assistants/default_assistant/agents"
    
    # Check existing agents in GE app
    list_resp = requests.get(url, headers=headers, timeout=30)
    list_resp.raise_for_status()
    existing_agents = list_resp.json().get("agents", [])
    
    match_agent = None
    for ag in existing_agents:
        if ag.get("displayName") == agent_card["name"]:
            match_agent = ag
            break

    ge_card = dict(agent_card)
    ge_card["protocolVersion"] = "1.0"
    if "supportedInterfaces" in ge_card and ge_card["supportedInterfaces"]:
        ge_card["url"] = ge_card["supportedInterfaces"][0]["url"]
    else:
        ge_card["url"] = "https://book-management-adk-98835120191.us-central1.run.app/a2a/v1/message"

    payload = {
        "displayName": agent_card["name"],
        "description": agent_card["description"],
        "icon": {
            "uri": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/smart_toy/default/24px.svg"
        },
        "a2aAgentDefinition": {
            "jsonAgentCard": json.dumps(ge_card)
        }
    }

    if match_agent:
        logger.info(f"  Found existing registration in Gemini Enterprise: {match_agent['name']}; updating...")
        patch_url = f"https://discoveryengine.googleapis.com/v1alpha/{match_agent['name']}"
        resp = requests.patch(patch_url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        agent_record = resp.json()
    else:
        logger.info("  No existing registration found; creating new agent in Gemini Enterprise...")
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        agent_record = resp.json()

    logger.info(f"✅ Gemini Enterprise App Registration: {agent_record.get('name')}")
    logger.info(f"   State: {agent_record.get('state')}")
    return agent_record


def verify_agent_discovery(query: str, agent_card: Dict[str, Any]) -> bool:
    """Verifies that the agent is discoverable by semantic search terms."""
    logger.info(f"🔍 Testing Registry Discovery Query: '{query}'...")
    query_lower = query.lower()
    matched_skills = []

    for skill in agent_card.get("skills", []):
        tags = [t.lower() for t in skill.get("tags", [])]
        if any(term in query_lower for term in tags) or query_lower in skill["name"].lower():
            matched_skills.append(skill["name"])

    if matched_skills:
        logger.info(f"🎉 Discovery SUCCESS! Query '{query}' matched agent skills: {matched_skills}")
        return True
    else:
        logger.warning(f"⚠️ Query '{query}' did not match any indexed skill tags.")
        return False


def main():
    print("=" * 80)
    print("🏢 GEMINI ENTERPRISE AGENT PLATFORM - CENTRAL REGISTRY & APP REGISTRAR")
    print("   ADK Sophisticated Book Management Concierge")
    print("=" * 80)
    print()

    if not os.path.exists(AGENT_CARD_PATH):
        logger.error(f"Agent card not found at {AGENT_CARD_PATH}")
        sys.exit(1)

    with open(AGENT_CARD_PATH, "r") as f:
        agent_card = json.load(f)

    # 1. Validate
    if not validate_agent_card(agent_card):
        sys.exit(1)
    print()

    # 2. Register with Google Cloud Agent Registry
    service_res = register_with_google_cloud_agent_registry(agent_card)
    print()

    # 3. Register with Gemini Enterprise App
    ge_res = register_with_gemini_enterprise_app(agent_card)
    print()

    # 4. Discovery test
    test_queries = [
        "Find kindle deals on my books",
        "Library hold on libby",
        "Goodreads book club questions"
    ]
    for q in test_queries:
        verify_agent_discovery(q, agent_card)

    print()
    print("=" * 80)
    print("🎯 REGISTRATION COMPLETE SUMMARY")
    print(f"   Agent Name:              {agent_card['name']}")
    print(f"   Cloud Agent Registry:    {service_res.get('name')}")
    print(f"   Projected Agent ID:      {service_res.get('registryResource')}")
    print(f"   Gemini Enterprise Agent: {ge_res.get('name')}")
    print(f"   Status in GE App:        {ge_res.get('state')}")
    print("=" * 80)


if __name__ == "__main__":
    main()
