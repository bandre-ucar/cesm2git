#!/usr/bin/env bash
TAGS=( `git tag`
)

for tag in ${TAGS[@]}; do
    git tag -d ${tag}
done

git checkout clm
git reset --hard master
git checkout cesm2git
