# React Dashboard

This directory contains all code necessary for the reach dashboard. 
It's structure is:
- `node_modules`: where installed packages are stored, kept out of source control
- `public`: Project metadata files
- `src`: Majority of relevant source code
  - `components`: This is where react components go. They are divided between `common` for components on every page, `results` for components relating to viewing results, and `search` for components relating to submiting new exsclaim queries. 
  - `services`: This houses the API request code, that components needing api connections will import.
- `package-lock.json` and  `package.json`: similar to a python `requirements.txt`

## Credit

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

