#!/bin/bash

# DB 구축 스크립트
# 가상환경을 미리 설정해야합니다.
# 실행 시점에 설정 파일 경로 강제 지정

python services/recommendation/app/modules/make_db/refiner.py
# python services/recommendation/app/modules/make_db/kg_builder.py
# python services/recommendation/app/modules/make_db/visualize_graph.py
# open graph_viz.html
