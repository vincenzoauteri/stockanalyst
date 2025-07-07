
## IMPORTANT!!!

When working on this application:

1. **The application runs in separate Docker containers that restart every time the source code is changed** - Every time you make a change, test in the containers accessing through the exposed services or with docker exec commands
2. **First make a plan** of what you plan to modify and ask for confirmation
3. **When implementing a new task, increase the app version (also visible in the frontend** When you test, make sure you you are testing against the updated app. 
4. **After each change**, run linting and tests to confirm everything is working correctly. Perform regression tests on database, frontend, backend, and API calls
5. **If the change does not work, do not keep trying new things.** Log the part that fails extensively and try to debug from the logs
6. **Git commit after each successful change** Keep commit messages short.
7. **Be professional** Be thorough and careful in uour analysis. Don't use emoji or exclamation marks, keep a professional, detached tome.

