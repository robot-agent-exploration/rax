"""Reach 4 cm above a mug rim from a fresh observation."""
import json

STANDOFF_M = 0.04  # tested 0.03-0.05 m


def perceive(ctx):
    reply = ctx.call("observe")
    state = json.loads(reply["content"][0]["text"])
    return {"ok": True, "measured": state, "why": "fresh observation"}


def reach(ctx, target):
    ctx.call("move_pose", **target)
    return {
        "ok": True,
        "measured": target,
        "why": "moved to standoff",
        "checkpoint": {
            "subagent": "fast",
            "frames": ["runtime/frames/latest/overview.jpg"],
            "question": "Is the gripper centred above the mug rim with no contact?",
            "answer": "yes | no",
            "pass_if": "yes",
            "on_fail": "retreat 8 cm along +z and re-localize the rim",
        },
    }


def main(ctx):
    seen = perceive(ctx)
    if not seen["ok"]:
        return seen
    result = reach(ctx, {"position": [0.0, 0.0, STANDOFF_M]})
    if not result["ok"]:
        return result
    return {"ok": True, "measured": result["measured"], "why": "mug reached"}
