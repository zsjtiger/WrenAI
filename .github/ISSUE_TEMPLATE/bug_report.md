---
name: Bug report
about: Create a report to help us improve
title: ''
labels: bug
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Desktop (please complete the following information):**
- OS: [e.g. iOS]
- Browser [e.g. chrome, safari]

**Janus AI Information**
- Version: [e.g, 0.1.0]

**Additional context**
Add any other context about the problem here.

**Relevant log output**
- Please share `config.yaml` with us, it should be located at `~/.janusai/config.yaml`.
- Please share your logs with us with the following command:
    ```bash
    docker logs janusai-janus-ui-1 >& janusai-janus-ui.log && \
    docker logs janusai-janus-ai-service-1 >& janusai-janus-ai-service.log && \
    docker logs janusai-janus-engine-1 >& janusai-janus-engine.log
    ```
