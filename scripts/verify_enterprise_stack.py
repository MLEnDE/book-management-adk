"""
End-to-End Enterprise Stack Verification Script for Gemini Enterprise Agent Platform.
Tests the 3 foundational pillars:
1. Agent Runtime Deployment & Health Probes (/health, /healthz, /readyz)
2. Central Agent Registry Discovery & A2A v1.0 Agent Card (/.well-known/agent-card.json)
3. Gemini Enterprise App Chat Interface & A2UI Protocol (/a2a/v1/message, /a2a/v1/action)
"""

import os
import sys
import json
from fastapi.testclient import TestClient

# Ensure package path is resolved
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from book_management_adk.server import app

client = TestClient(app)


def test_agent_runtime_probes():
    print("=" * 80)
    print("🧪 [STAGE 1] TESTING AGENT RUNTIME LIFECYCLE & HEALTH PROBES")
    print("=" * 80)

    # 1. /health
    resp = client.get("/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    print(f"✅ /health probe: {resp.json()}")

    # 2. /healthz (Liveness)
    resp = client.get("/healthz")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    print(f"✅ /healthz liveness probe: {resp.json()}")

    # 3. /readyz (Readiness)
    resp = client.get("/readyz")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    print(f"✅ /readyz readiness probe: {resp.json()}")
    print("🎉 Stage 1 Passed: Agent Runtime probes fully operational!\n")


def test_central_agent_registry_discovery():
    print("=" * 80)
    print("🧪 [STAGE 2] TESTING CENTRAL AGENT REGISTRY DISCOVERY & A2A AGENT CARD")
    print("=" * 80)

    resp = client.get("/.well-known/agent-card.json")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    agent_card = resp.json()

    print(f"✅ Retrieved Agent Card for: '{agent_card['displayName']}'")
    print(f"   URN:              {agent_card['name']}")
    print(f"   Protocol:         A2A v{agent_card['protocolVersion']}")
    print(f"   SPIFFE Identity:  {agent_card['spiffeId']}")
    print(f"   Declared Skills:  {len(agent_card['skills'])} skills")
    for s in agent_card["skills"]:
        print(f"     - [{s['id']}] {s['name']}")

    print(f"   Declared Tools:   {len(agent_card['tools'])} tools")
    mutating = [t["name"] for t in agent_card["tools"] if t.get("destructiveHint")]
    print(f"   HITL Mutating:    {mutating}")

    # Verify App Hub properties
    app_hub = agent_card.get("registryMetadata", {}).get("appHubProperties", {})
    assert app_hub.get("businessService") == "Personal Reading Automation"
    print(f"✅ App Hub Business Service Verified: '{app_hub.get('businessService')}'")
    print("🎉 Stage 2 Passed: Central Agent Registry discovery spec validated!\n")


def test_gemini_chat_interface_and_a2ui():
    print("=" * 80)
    print("🧪 [STAGE 3] TESTING GEMINI ENTERPRISE CHAT INTERFACE & A2UI PROTOCOL")
    print("=" * 80)

    # 1. Chat App Extension Manifest
    ext_resp = client.get("/api/v1/chat/extension-manifest")
    assert ext_resp.status_code == 200
    ext_manifest = ext_resp.json()
    print(f"✅ Chat App Extension Manifest: '{ext_manifest['displayName']}'")
    print(f"   Slash commands supported: {[c['command'] for c in ext_manifest['chatInterfaceConfig']['slashCommands']]}")

    # 2. User queries for Kindle Deals (/deals)
    print("\n👉 Simulating user in Gemini Enterprise Chat: '/deals'")
    chat_resp = client.post("/a2a/v1/message", json={"message": "/deals"})
    assert chat_resp.status_code == 200
    data = chat_resp.json()

    print(f"💬 Agent Markdown Response:\n{data['text']}")
    surfaces = data.get("a2ui_surfaces", [])
    print(f"🖼️  A2UI Material 3 Surfaces Emitted: {len(surfaces)}")
    assert len(surfaces) > 0, "Expected A2UI confirmation cards for deals"

    first_card = surfaces[0]
    print(f"   Surface ID: {first_card['surface_id']}")
    print(f"   Surface Title: {first_card['title']}")

    # 3. Simulate User Clicking "Confirm & Execute" on the interactive A2UI Confirmation Card
    btn_components = []
    def find_buttons(comp):
        if comp.get("type") == "Button":
            btn_components.append(comp)
        for child in comp.get("children", []) or []:
            find_buttons(child)

    for c in first_card.get("components", []):
        find_buttons(c)

    print(f"   Found {len(btn_components)} interactive buttons on Material 3 Card:")
    confirm_action = None
    for b in btn_components:
        label = b.get("props", {}).get("label")
        action = b.get("props", {}).get("action", {})
        print(f"     🔘 Button: '{label}' -> Action: {action.get('action_id')}, Params: {action.get('params')}")
        if label == "Confirm & Execute":
            confirm_action = action

    assert confirm_action is not None, "Expected Confirm & Execute action"

    # 4. Dispatch the action event back to /a2a/v1/action
    print(f"\n🖱️  Simulating user clicking '{confirm_action.get('action_id')}' button...")
    action_resp = client.post("/a2a/v1/action", json={
        "action_id": confirm_action.get("action_id"),
        "params": confirm_action.get("params")
    })
    assert action_resp.status_code == 200
    action_data = action_resp.json()
    print(f"✅ Action Resolution Result:")
    print(f"   Success: {action_data.get('success')}")
    print(f"   Message: {action_data.get('message')}")
    print(f"   Updated A2UI Surface Title: {action_data.get('surface', {}).get('title')}")

    print("\n🎉 Stage 3 Passed: Gemini Enterprise Chat App & A2UI Protocol fully verified!\n")


def main():
    print("=" * 80)
    print("🚀 RUNNING FULL GEMINI ENTERPRISE AGENT PLATFORM STACK VERIFICATION")
    print("   Runtime -> Registry -> Client Exposure (A2UI)")
    print("=" * 80)
    print()

    test_agent_runtime_probes()
    test_central_agent_registry_discovery()
    test_gemini_chat_interface_and_a2ui()

    print("=" * 80)
    print("🏆 ALL THREE ENTERPRISE STACK LAYERS ARE VERIFIED AND OPERATIONAL!")
    print("=" * 80)


if __name__ == "__main__":
    main()
