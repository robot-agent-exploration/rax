# Mug rim reach

Run the controller from a development wrapper outside this directory:

```python
# experiments/run_controller.py
import sys
from api.runtime import Context

sys.path.insert(0, "code/mug-reach")
from controller import main

with Context() as ctx:
    print(main(ctx))
```

`controller.py:main(ctx)` re-observes, moves to a 4 cm standoff above the rim, and
returns `{ok, measured, why}`. Preconditions: mug upright on the table, robot at
neutral.

## Perception checkpoints

| Step | Subagent | Frames | Question | Expected answer | Pass if | On fail |
|---|---|---|---|---|---|---|
| reach | fast | overview after the move | Is the gripper centred above the mug rim with no contact? | yes | yes | retreat 8 cm along +z and re-localize |
