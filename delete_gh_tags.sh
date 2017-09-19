#!/usr/bin/env bash
TAGS=` git tag | sed -e 's/^/:/' | paste -sd " " -`
# echo $TAGS
git push --force ncar $TAGS

#TAGS=(`git tag`)
#for tag in ${TAGS[@]}; do
#    git push --delete ncar ${tag}
#done
