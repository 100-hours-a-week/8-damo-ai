import time
import random
import asyncio
from datetime import datetime
from typing import Any, Dict, List

async def random_delay_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    테스트를 위해 0~10초 사이의 임의의 지연을 발생시키는 노드입니다.
    """
    delay = random.uniform(0, 10)
    await asyncio.sleep(delay)
    return {
        "status_message": [f"임의 지연 발생: {delay:.2f}초"]
    }

async def record_start_time_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    그래프의 시작 시간을 기록하고 초기 메시지를 추가하는 공통 노드입니다.
    """
    now = datetime.now()
    return {
        "process_start_time": now,
        "status_message": [f"그래프 실행 시작: {now.strftime('%Y-%m-%d %H:%M:%S')}"]
    }

async def record_end_time_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    그래프의 종료 시간을 기록하고 총 소요 시간을 계산하여 메시지를 추가하는 공통 노드입니다.
    """
    start_time = state.get("process_start_time")
    end_time = datetime.now()
    
    duration = 0.0
    if start_time:
        duration = (end_time - start_time).total_seconds()
        message = f"그래프 실행 완료: {end_time.strftime('%Y-%m-%d %H:%M:%S')} (총 소요 시간: {duration:.4f}초)"
    else:
        message = f"그래프 실행 완료: {end_time.strftime('%Y-%m-%d %H:%M:%S')} (시작 시간 기록 없음)"
        
    return {
        "status_message": [message],
        "process_time": float(f"{duration:.4f}")
    }
