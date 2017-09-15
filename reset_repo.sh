#!/usr/bin/env bash
TAGS=( `git tag`
)

for tag in ${TAGS[@]}; do
    git tag -d ${tag}
done

git add --update
git stash
git checkout clm
git reset --hard a0a50e5df
git checkout master
git reset --hard a0a50e5df
git checkout cesm2git
git stash pop
git add --update

