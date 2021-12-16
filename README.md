## How to develop this XBlock

- If you made any changes in the translation files make sure to run `msgfmt text.po -o text.mo` locally in the `gradefetcher/translations/fr_CA/LC_MESSAGES/` folder or other languages folder to update the language files and after that push the changes to the branch.
- Make a deployment via ansible using the ansible tag `install:app-requirements`.
- Restart Open edX services on the server.
