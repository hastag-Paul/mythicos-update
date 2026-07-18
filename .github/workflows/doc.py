name: Rename manpages Mint → MythicOS

on:
  push:
    branches:
      - main
      - master

jobs:
  rename:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Rename manpages
        run: |
          MAN_DIR="doc/man"

          declare -A RENAMES=(
            ["mint-release-upgrade.8"]="mythicos-release-upgrade.8"
            ["mintupdate.8"]="mythicos-update.8"
            ["mintupdate-cli.8"]="mythicos-update-cli.8"
            ["mintupdate-launcher.8"]="mythicos-update-launcher.8"
          )

          for OLD in "${!RENAMES[@]}"; do
            NEW="${RENAMES[$OLD]}"
            if [ -f "$MAN_DIR/$OLD" ]; then
              echo "Renaming $OLD → $NEW"
              mv "$MAN_DIR/$OLD" "$MAN_DIR/$NEW"
            else
              echo "Skipping $OLD (not found)"
            fi
          done

      - name: Commit changes
        run: |
          if git status --porcelain | grep -q .; then
            git config user.name "GitHub Actions"
            git config user.email "actions@github.com"
            git add doc/man/
            git commit -m "Auto-rename manpages Mint → MythicOS"
            git push
          else
            echo "No changes to commit."
          fi
