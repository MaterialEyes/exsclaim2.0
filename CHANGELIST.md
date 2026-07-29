# Version 2.5.1
## API
- Switched the session-based cookies to JWTs.
- Users can now delete results from the database (assuming that the run was started while they were logged in to their account)
- Users can now delete their account
- EXSCLAIM can block IP's belonging to users trying to exploit obvious URL paths (.env, .git, etc)
- Individual items will check the owner before yielding any results
- Users can merge an account they created with their email with an account they created with their ORCID.
- Users can update their usernames.
- `/user/login` and `/user/signup` now use a BaseModel as the way to retrieve information, which changes how users post to them.

## Dashboard
- Fixed a bug that wouldn't allow users to log in with their email and password
- Added HTML `<time>` tags to the previous runs

## Pipeline
- Moved the compressing methods inside of the `Pipeline` class.
- All of the tools can now act as context managers, automatically loading and unloading, even if there's an error.

### Database
- Added a foreign key constraint that requires articles in `results.article` to attach to runs in `results.results`.
- Moved the Postgres configuration information into a `pydantic.BaseSettings` class.

### Captions
- The `LlamaCPP` class now handles its environment variable through pydantic's BaseSettings. 
- `LlamaCPP` can listen to the llama-server's Server Side Events (SSE) to see when the model is loaded.
- `LlamaCPP` can now accept the path to a cert file if the Llama server's SSL certificate is signed with a local certificate authority (CA).
- LLMs now have the option to accept optional API keys, in case the LLM server responds differently to anonymous users versus authorized users.

### Figures
- All scale lines are saved as results instead of just the first scale line.

## Other
- Moved the tests outside of the module
- Added webhooks as a notification type
- Realized that the beta versions of 2.5.1* have been listed as 2.5.0b*, even though 2.5.0 was already created.
- Changed the ExsclaimSettings to directly parse environment variables into `pathlib.Path`s when needed.

# Version 2.5.0
## API
- Users can now allow other users publicize their runs so other viewers can see them

## Dashboard
- Using Dash's built-in pages ability instead of manually choosing the page's main component given the URL.
- Added a banner to the UI for temporary notifications.
- Updated the components used for showing results, as well as squashing bugs when the filtering was not working.

### Captions
- Captions and keywords are parsed from the same request instead of two separate requests.
- Captions include HTML tags when they're sent to the LLM, so any formatting should show up on the Results page.
- Moved the LLMs from `exsclaim/captions` to `exsclaim/llms`.
- Added Llama.CPP as a server.
- Added the ability to send malformed responses back to the LLM to fix, along with the error from Pydantic.

### Figures
- Updated the type hints for some of the files in `exsclaim/figures/scale`
- Added a second YOLOv11 model to find the bounding boxes of the subfigures' labels.

## Training
- Added a training page that allows users to use previous runs to create a training set that can be used to update the YOLO and local LLMs.

## Other
- Removed `--force-ollama` as an argument when starting up. Users will need to ensure their Ollama server is running before EXSCLAIM is called.
- `initialize_db` is now an argument that can be passed to any of the major commands instead of its own command.
- Changed the erroneous version number from 2.6.0 to 2.4.3 in ChangeList.md.

# Version 2.4.3
## API
- Created users to for private runs
- Added the ability to log in with ORCID instead of using an email and password
- Categorized the pages by route
- Update the way environment variables are integrated into the codebase

## Dashboard
- Added a login/signup page for users
- Added a page to see all previous runs available to the user (or all runs done by guests)
- Added the ability to specify NTFY options through the Dashboard for queries

## Database
- Now uses UUIDv7 instead of UUIDv4

## Pipeline
- Configuration values are not held in BaseSettings classes to ensure no variables are accidentally hard-coded.
- Added HTML classes for the JournalScraper to make it easier to take advantage of internal methods for either Dynamic or Static pages.
- NTFY notifications contain a link to the website if one is provided.