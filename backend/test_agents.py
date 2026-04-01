import logging
import os
import sys

# 解决导库问题
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.supervisor_agent import SupervisorAgent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_legal_consulting():
    print("=== 测试场景 1：法律咨询 ===")
    supervisor = SupervisorAgent()
    query = "由于噪音扰民，我该如何起诉邻居？"
    response = supervisor.run_workflow(query)
    print(f"\n用户提问: {query}")
    print(f"\n系统响应:\n{response}")
    print("=" * 30)

def test_document_drafting():
    print("\n=== 测试场景 2：文书起草 ===")
    supervisor = SupervisorAgent()
    query = "帮我写一个简单的民事起诉状，原告是张三，被告是李四，由于他借我5000块钱一年多没还。法院是北京市海淀区人民法院。"
    response = supervisor.run_workflow(query)
    print(f"\n用户提问: {query}")
    print(f"\n系统响应:\n{response}")
    print("=" * 30)

if __name__ == "__main__":
    # 注意：运行此测试需要配置好 config.py 中的 LLM API Key
    try:
        test_legal_consulting()
        test_document_drafting()
    except Exception as e:
        logger.error(f"自动化测试失败: {e}")
