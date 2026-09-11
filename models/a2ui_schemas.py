"""
A2UI (Agent-to-User Interface) Protocol Models and Blueprints.
Enables declarative Google Material 3 (GM3) UI components and interactive
Human-In-The-Loop confirmation cards within the Gemini Enterprise Chat App.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class A2UIAction(BaseModel):
    """Action payload triggered by user interaction with an A2UI button or form."""
    action_id: str = Field(..., description="Action identifier, e.g., 'resolve_approval'")
    event: str = Field(default="click", description="Event type: 'click', 'submit', 'change'")
    params: Dict[str, Any] = Field(default_factory=dict, description="Contextual parameters passed back to backend")


class A2UIComponent(BaseModel):
    """Declarative Material 3 UI component descriptor."""
    id: str = Field(..., description="Unique component ID within the surface")
    type: str = Field(..., description="Component type: 'Card', 'Text', 'Badge', 'Button', 'Chip', 'Row', 'Column', 'Divider'")
    props: Dict[str, Any] = Field(default_factory=dict, description="Visual and behavioral properties")
    children: Optional[List["A2UIComponent"]] = Field(default=None, description="Nested child components")


class A2UISurface(BaseModel):
    """Top-level A2UI surface emitted by agent to Gemini Enterprise chat."""
    protocol_version: str = Field(default="a2ui-v0.9")
    surface_id: str = Field(..., description="Unique surface ID")
    surface_type: str = Field(default="interactive_card", description="Surface category: 'interactive_card', 'dashboard', 'form'")
    title: str = Field(..., description="Surface title")
    components: List[A2UIComponent] = Field(default_factory=list, description="Root component hierarchy")


# --- Builder Helpers for Gemini Enterprise Chat UI ---

def build_hitl_approval_card(req: Dict[str, Any]) -> A2UISurface:
    """
    Constructs an interactive A2UI Confirmation Card with physical buttons
    for Human-In-The-Loop approval directly in the Gemini Enterprise Chat interface.
    """
    req_id = req.get("request_id", "")
    title = req.get("title", "Approval Request")
    desc = req.get("description", "")
    risk = req.get("risk_level", "medium").upper()
    action_type = req.get("action_type", "")
    payload = req.get("payload", {})

    # Color tokens based on risk
    badge_variant = "error" if risk == "HIGH" else ("warning" if risk == "MEDIUM" else "info")

    components: List[A2UIComponent] = [
        A2UIComponent(
            id=f"card_{req_id}",
            type="Card",
            props={
                "variant": "elevated",
                "padding": "medium",
                "borderHighlight": risk == "HIGH"
            },
            children=[
                # Header row: Title + Risk Badge
                A2UIComponent(
                    id=f"hdr_row_{req_id}",
                    type="Row",
                    props={"justify": "space-between", "align": "center"},
                    children=[
                        A2UIComponent(
                            id=f"title_{req_id}",
                            type="Text",
                            props={"text": title, "variant": "titleMedium", "weight": "bold"}
                        ),
                        A2UIComponent(
                            id=f"badge_{req_id}",
                            type="Badge",
                            props={"label": f"RISK: {risk}", "variant": badge_variant}
                        )
                    ]
                ),
                # Details description
                A2UIComponent(
                    id=f"desc_{req_id}",
                    type="Text",
                    props={"text": desc, "variant": "bodyMedium", "color": "secondary"}
                ),
                *(
                    [
                        A2UIComponent(
                            id=f"link_{req_id}",
                            type="Text",
                            props={
                                "text": f"🔗 **Secure Deal Website:** [View & Purchase on Amazon Kindle ↗]({deal_url})\nDirect URL: `{deal_url}`",
                                "variant": "bodySmall",
                                "color": "primary"
                            }
                        )
                    ] if (deal_url := payload.get("deal_url") or payload.get("url") or req.get("metadata", {}).get("deal_url")) else []
                ),
                # Divider
                A2UIComponent(id=f"div_{req_id}", type="Divider", props={}),
                # Action Buttons Row
                A2UIComponent(
                    id=f"btn_row_{req_id}",
                    type="Row",
                    props={"justify": "flex-end", "gap": "small"},
                    children=[
                        *(
                            [
                                A2UIComponent(
                                    id=f"link_btn_{req_id}",
                                    type="Button",
                                    props={
                                        "label": "Open Deal Site ↗",
                                        "variant": "text",
                                        "color": "primary",
                                        "url": deal_url
                                    }
                                )
                            ] if (deal_url := payload.get("deal_url") or payload.get("url") or req.get("metadata", {}).get("deal_url")) else []
                        ),
                        A2UIComponent(
                            id=f"reject_btn_{req_id}",
                            type="Button",
                            props={
                                "label": "Decline",
                                "variant": "outlined",
                                "color": "secondary",
                                "action": A2UIAction(
                                    action_id="resolve_approval",
                                    params={"request_id": req_id, "approved": False}
                                ).model_dump()
                            }
                        ),
                        A2UIComponent(
                            id=f"approve_btn_{req_id}",
                            type="Button",
                            props={
                                "label": "Confirm & Execute",
                                "variant": "filled",
                                "color": "primary",
                                "action": A2UIAction(
                                    action_id="resolve_approval",
                                    params={"request_id": req_id, "approved": True}
                                ).model_dump()
                            }
                        )
                    ]
                )
            ]
        )
    ]

    return A2UISurface(
        surface_id=f"surface_{req_id}",
        title=f"Approval Gate: {title}",
        components=components
    )


def build_action_result_surface(request_id: str, title: str, message: str, success: bool) -> A2UISurface:
    """Builds an A2UI feedback surface replacing the confirmation card after user clicks."""
    return A2UISurface(
        surface_id=f"result_{request_id}",
        title="Action Resolution",
        components=[
            A2UIComponent(
                id=f"result_card_{request_id}",
                type="Card",
                props={"variant": "outlined", "padding": "medium"},
                children=[
                    A2UIComponent(
                        id=f"result_title_{request_id}",
                        type="Text",
                        props={
                            "text": f"✅ {title}" if success else f"❌ {title}",
                            "variant": "titleMedium",
                            "weight": "bold"
                        }
                    ),
                    A2UIComponent(
                        id=f"result_msg_{request_id}",
                        type="Text",
                        props={"text": message, "variant": "bodyMedium"}
                    )
                ]
            )
        ]
    )
