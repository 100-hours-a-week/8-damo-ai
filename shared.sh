#!/bin/bash

# dev/shared와 dev/test를 현재 작업중인 폴더에 가져오기
git restore --source origin/dev shared/
git restore --source origin/dev test/
git restore --source origin/dev requirements.txt