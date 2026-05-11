# Version 2.6.0
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