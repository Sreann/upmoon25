# ROS Skills Search

This file records ROS/ROS2-related agent skills found online. These are candidates only; do not install them blindly on the robot.

## Summary

There does not appear to be a high-install, official ROS 2 skill in the main skills.sh ecosystem. The best candidates are community skills hosted on GitHub or mirrored by third-party skill indexes.

Local copies of the useful candidates were vendored for review under `lunar/skills/vendor/`.

The most relevant categories are:

- ROS 2 CLI / rclpy interaction skills
- ROS / ROS2 via rosbridge WebSocket skills
- ROS 2 engineering standards and best-practice skills

For this robot, the most useful direction is probably:

1. Use a ROS 2 engineering skill for code/design guidance.
2. Optionally inspect a ROS 2 CLI skill for ideas.
3. Do not give any agent direct robot-control powers without safety review.

## Candidate Skills

### 1. ros2-skill

Controls and monitors ROS 2 robots directly through an rclpy-based CLI.

- Source: `adityakamath/ros2-skill`
- Local copy: `lunar/skills/vendor/ros2-skill`
- Mirror: https://skills.rest/skill/ros2-skill
- Other listing: https://playbooks.com/skills/openclaw/skills/ros2-skill
- Category: ROS 2 control / monitoring
- Requires: Python, ROS 2 environment, `rclpy`
- Reported installs: 0 on skills.rest listing
- Use case:
  - List topics/nodes/services/actions
  - Inspect parameters
  - Publish/subscribe from CLI
  - Structured JSON output for agent workflows

Possible install references:

```text
https://github.com/adityakamath/ros2-skill/archive/main.zip#ros2-skill
```

Playbooks listing:

```bash
npx playbooks add skill openclaw/skills --skill ros2-skill
```

Assessment:

- Interesting and directly relevant.
- Better suited for development diagnostics than autonomous operation.
- Needs safety review before use around a live robot because it can publish robot commands.

### 2. ros-skill

Controls and monitors ROS/ROS2 robots through rosbridge WebSocket.

- Source: `lpigeon/ros-skill`
- GitHub: https://github.com/lpigeon/ros-skill
- Local copy: `lunar/skills/vendor/ros-skill`
- Listing: https://playbooks.com/skills/openclaw/skills/ros-skill
- Category: ROS/ROS2 via rosbridge
- Requires: `websocket-client`, rosbridge running on robot
- GitHub stars at search time: low, around 20
- Use case:
  - Topic list/type/details
  - Topic publish/subscribe
  - Service list/call
  - Node list/details
  - Parameters
  - Actions

Install reference:

```bash
npx playbooks add skill openclaw/skills --skill ros-skill
```

Assessment:

- Architecturally relevant to a web dashboard because it uses rosbridge.
- Could provide useful command patterns for dashboard bridge design.
- Not recommended as a direct control path for the competition robot without strict command filtering and watchdogs.

### 3. ros2-engineering-skills

Production-grade ROS 2 development guidance.

- Source: `dbwls99706/ros2-engineering-skills`
- GitHub: https://github.com/dbwls99706/ros2-engineering-skills
- Local copy: `lunar/skills/vendor/ros2-engineering-skills`
- Listing: https://www.awesomeskills.dev/en/skill/dbwls99706-ros2-engineering-skills
- Other listing: https://skillsmp.com/skills/dbwls99706-ros2-engineering-skills-skill-md
- Category: ROS 2 engineering guidance
- Covers:
  - ROS 2 workspaces
  - nodes
  - executors
  - QoS
  - ros2_control
  - Nav2
  - MoveIt 2
  - real-time concerns
  - deployment
  - Gazebo / simulation
  - rosbag2

Install reference from listing:

```bash
npx add-skill dbwls99706/ros2-engineering-skills
```

Assessment:

- Probably the most useful ROS skill for our project because it focuses on engineering practice, not direct robot control.
- Still community-maintained, so review before installing.
- Good candidate for code review and architecture work.

### 4. ros-integration

General ROS/ROS2 middleware integration skill.

- Source: appears under `majiayu000/claude-skill-registry`
- Local copy: `lunar/skills/vendor/ros-integration`
- Listing: https://eliteai.tools/agent-skills/ros-integration-1
- Category: ROS/ROS2 integration
- Reported stars/forks from listing: moderate
- Use case:
  - node development
  - launch files
  - package management
  - publishers/subscribers/services/actions
  - topic connectivity debugging

Install reference from listing:

```bash
npx add-skill https://github.com/majiayu000/claude-skill-registry/tree/main/skills/other/other/ros-integration
```

Assessment:

- Potentially useful, but source path is nested in a broad registry.
- Needs review before installation.
- Might overlap with `ros2-engineering-skills`.

### 5. ros2-standards

ROS 2 Python coding standards and guidance.

- Source: `uneezaismail/ros2-standards`
- Listing: https://smithery.ai/skills/uneezaismail/ros2-standards
- Category: ROS 2 Python standards
- Reported installs: very low
- Use case:
  - ROS 2 Humble Python code quality
  - maintainability
  - performance
  - physical AI robustness

Install reference:

```bash
npx @smithery/cli@latest skill add uneezaismail/ros2-standards
```

Assessment:

- Interesting but low signal.
- Some listed guidance may assume Python 3.11+, while ROS 2 Humble environments are often Python 3.10 on Ubuntu 22.04.
- Review carefully before using.
- Fetch status: not vendored; the listed GitHub repository returned "Repository not found."

## Recommendation

For this project, do not start by installing a direct ROS robot-control skill.

Recommended review order:

1. `ros2-engineering-skills`
2. `ros2-skill`
3. `ros-skill`
4. `ros-integration`
5. `ros2-standards`

Best immediate value:

- Use `ros2-engineering-skills` as reference material for ROS 2 architecture, QoS, Nav2, launch files, and rosbag workflows.
- Use `ros2-skill` only as inspiration for structured CLI diagnostics.
- Use `ros-skill` only if we intentionally adopt rosbridge for the dashboard bridge.

## Safety Notes

Any skill that can publish ROS commands is dangerous around a live robot.

Before installing or using a ROS control skill:

- Confirm it cannot publish motion commands without explicit approval.
- Confirm it cannot bypass emergency stop.
- Confirm command topics are allowlisted.
- Confirm velocity commands have duration limits.
- Confirm robot-side watchdogs stop motion when commands stop.
- Never let browser/agent state be the only safety layer.

For the dashboard, prefer a project-specific bridge with a narrow command API over a general-purpose ROS command skill.

## Search Notes

Searches performed:

- `site:skills.sh ROS skill robotics ROS2`
- `site:skills.sh ros2 skill`
- `site:skills.sh robotics skill ROS`
- `site:skills.sh rosbridge roslibjs skill`
- `GitHub ROS2 agent skill SKILL.md`
- `GitHub ros2 claude skill robotics SKILL.md`
- `GitHub ROS agent skills robotics`
- `"ROS 2" "SKILL.md" "skills"`

Result:

- Main skills.sh search did not surface a strong official ROS skill.
- Broader web search found community ROS skills across skills.rest, GitHub, Playbooks, Awesome Skills, Smithery, and EliteAI.
