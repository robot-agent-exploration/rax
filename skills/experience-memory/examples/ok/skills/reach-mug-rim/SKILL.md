---
name: learned-reach-mug-rim
description: Reach 4 cm above a mug rim when the mug is upright and visible on the table
---

# Reach above mug rim

- Applies when: mug body and rim are visible on the table in the overview camera
- Avoid when: mug is on its side, occluded, or off the table
- Executed action: `<move_pose>` to 4 cm above the localized rim, current gripper orientation
- Pose recipe: rim surface point from the overview camera, robot frame, +0.04 m along z
- Actions: localize several rim pixels; take the median; preview the pose; move; observe
- Expected effect: gripper centred above the rim with no contact
- Recovery: if the preview reports a collision, retreat 8 cm along +z and re-localize
