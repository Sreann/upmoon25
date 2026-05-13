# Vendored ROS Skill References

These are local, reviewable copies of ROS-related skills found online. They are stored here as reference material for the lunar robot project.

They are not automatically enabled as Codex skills, and they should not be treated as trusted robot-control software.

## Included

### ros2-engineering-skills

- Source: https://github.com/dbwls99706/ros2-engineering-skills
- Local path: `lunar/skills/vendor/ros2-engineering-skills`
- Best use: ROS 2 engineering guidance, QoS, Nav2, TF, perception, simulation, testing, deployment.
- Recommendation: Most useful reference.

### ros2-skill

- Source: https://github.com/adityakamath/ros2-skill
- Local path: `lunar/skills/vendor/ros2-skill`
- Best use: ROS 2 CLI diagnostics and structured command ideas.
- Caution: Includes direct ROS command/publish capabilities. Review carefully before use.

### ros-skill

- Source: https://github.com/lpigeon/ros-skill
- Local path: `lunar/skills/vendor/ros-skill`
- Best use: rosbridge/WebSocket interaction patterns.
- Caution: Direct ROS control over rosbridge is powerful and should be allowlisted.

### ros-integration

- Source: https://github.com/majiayu000/claude-skill-registry/tree/main/skills/other/other/ros-integration
- Local path: `lunar/skills/vendor/ros-integration`
- Best use: General ROS/ROS2 integration guidance.
- Caution: Came from a broad skill registry; review before relying on it.

## Not Included

### ros2-standards

The listed GitHub source `uneezaismail/ros2-standards` was unavailable when fetched. Keep it in the search notes as unresolved, but do not depend on it.

## Safety Policy

Do not use a vendored skill to command the live robot unless:

- The command path is explicitly approved.
- Velocity/motion topics are allowlisted.
- Robot-side watchdogs are active.
- Emergency stop remains independent.
- Commands have duration limits.
- The operator knows the skill can affect motion.

For the mission-control dashboard, prefer a narrow project-specific bridge over generic ROS command tooling.
