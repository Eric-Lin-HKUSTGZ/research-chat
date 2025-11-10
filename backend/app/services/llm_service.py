"""
LLM服务模块 - 集成keyu-ideation的研究计划生成功能
"""
import requests
import time
import os
from typing import Optional, Dict, Any
from app.core.config import Config

# 从keyu-ideation复制的提示模板
PROMPT_TEMPLATES = {
    "retrieve_query": """You are an expert at extracting keywords from user queries. 
Below, I will provide you with a user query in which the user expresses interest in developing a new research proposal. Your task is to extract up to two keywords that best capture the core research topic or methodology of interest to the user.

Each keyword must be:

1. A noun (or noun phrase),
2. Written in lowercase English,
3. Representative of the central concept or approach in the query.

Here is the user query:
User Query: {user_query}

Please output exactly one or two keywords—no more, no less—each as a lowercase English noun, separated by a comma and without any additional text, punctuation, or formatting.
""",
    "get_inspiration": """You are a professional research paper analyst skilled at drawing creative inspiration from academic literature. 
Below, I will provide a user query along with a set of related papers, including the latest, highly cited, and relevant works. Your task is to synthesize these papers holistically and propose one novel research inspiration that directly addresses the user's query.

Here is the information provided:
User Query: {user_query}
Related Papers: {paper}

Please synthesize these papers holistically—without analyzing each one individually—and propose one novel research inspiration that directly addresses the user's query. The inspiration should emerge from a deep understanding of the underlying assumptions, gaps, or unexplored opportunities in the existing literature, not merely by combining existing methods. Prioritize conceptual insight and originality over technical aggregation, and ensure the proposal is both innovative and closely aligned with the user's needs. Focus on delivering a concise, imaginative spark rooted in genuine scholarly insight. 
""",
    "generate_research_plan": """You are an experienced research proposal writer. 
Below, I will provide you with a user query, a set of related academic papers(including the latest, highly cited, and relevant works) and a novel research inspiration derived from a deep analysis of these papers. You are tasked with drafting a complete research proposal based on this information.

Here is the information provided:
User Query: {user_query}
Related Papers: {paper}
Inspiration: {inspiration}

Based on this information, please draft a complete research proposal that fulfills the following requirements:

1. The proposal must be grounded in the provided research inspiration—do not deviate from or replace it.
2. If the user specifies particular sections or components the proposal should include, follow those instructions exactly.
3. If no specific structure is given, organize the proposal into the following three sections:
  • Research Background – contextualize the problem and summarize key findings from the related literature,
  • Limitations of Current Work – identify critical gaps or shortcomings in existing approaches, and
  • Proposed Research Plan – detail the novel idea, methodology, and how it addresses the user's query and overcomes prior limitations.

Ensure the proposal is coherent, technically sound, and directly aligned with both the user's needs and the provided inspiration.
""",
    "critic_research_plan": """You are a rigorous research proposal reviewer. 
Below, I will provide you with a user query, a set of related academic papers(including the latest, highly cited, and relevant works), a novel research inspiration derived from a deep analysis of these papers abd a preliminary research proposal based on this inspiration. You are tasked with conducting a strict and critical evaluation of the proposal. 

Here is the information provided:
User Query: {user_query}
Related Papers: {paper}
Inspiration: {inspiration}
Preliminary Research Proposal: {research_plan}

Please conduct a strict and critical evaluation of the proposal. Identify its key weaknesses—such as high overlap with existing literature, lack of genuine novelty (e.g., merely combining existing methods without deeper insight), insufficient alignment with the stated inspiration, or failure to address core gaps in the field.
In addition to diagnosing these issues, provide clear, concrete, and actionable suggestions for how the proposal can be revised to enhance its originality, rigor, and relevance to the user's query.
""",
    "refine_research_plan": """You are a professional research proposal optimizer. 
Below, I will provide you with a user query, a preliminary research proposalc, a critical evaluation of the proposal and a clear revision suggestion. You are tasked with thoroughly revising the research proposal based on the feedback provided.

Here is the information provided:
User Query: {user_query}
Preliminary Research Proposal: {research_plan}
Critical evaluation of the proposal and clear revision suggestion: {criticism}

Please revise the research proposal thoroughly in light of the feedback, ensuring that the updated version fully aligns with both the original user query and the stated revision requirements. The revised proposal should clearly address the identified issues—such as lack of novelty, insufficient methodological detail, or misalignment with the user's goals—while maintaining coherence, rigor, and scientific plausibility. The refined proposal should fulfills the following requirements:
1. If the user specifies particular sections or components the proposal should include, follow those instructions exactly.
2. If no specific structure is given, organize the proposal into the following three sections:
  • Research Background – contextualize the problem and summarize key findings from the related literature,
  • Limitations of Current Work – identify critical gaps or shortcomings in existing approaches, and
  • Proposed Research Plan – detail the novel idea, methodology, and how it addresses the user's query and overcomes prior limitations.
"""
}


def get_newest_paper(query, max_results=None, max_retries=None):
    """获取最新论文"""
    max_results = max_results or getattr(Config, 'MAX_PAPERS_PER_QUERY', 3)
    max_retries = max_retries or getattr(Config, 'SEMANTIC_SCHOLAR_MAX_RETRIES', 20)
    timeout = getattr(Config, 'SEMANTIC_SCHOLAR_TIMEOUT', 10)
    
    url = f"http://api.semanticscholar.org/graph/v1/paper/search/bulk"
    params = {"query": query, "fields": "title,abstract", "sort": "publicationDate:desc"}
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            data = response.json()
            
            if 'data' in data:
                return data['data'][:max_results]
            else:
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"获取最新论文失败: {e}，{1}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                time.sleep(1)
                continue
            else:
                print(f"获取最新论文最终失败: {e}")
                return []
    
    return []


def get_highly_cited_paper(query, max_results=None, max_retries=None):
    """获取高引用论文"""
    max_results = max_results or getattr(Config, 'MAX_PAPERS_PER_QUERY', 3)
    max_retries = max_retries or getattr(Config, 'SEMANTIC_SCHOLAR_MAX_RETRIES', 20)
    timeout = getattr(Config, 'SEMANTIC_SCHOLAR_TIMEOUT', 10)
    
    url = f"http://api.semanticscholar.org/graph/v1/paper/search/bulk"
    params = {"query": query, "fields": "title,abstract", "sort": "citationCount:desc"}
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)        
            data = response.json()
            
            if 'data' in data:
                return data['data'][:max_results]
            else:
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"获取高引用论文失败: {e}，{1}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                time.sleep(1)
                continue
            else:
                print(f"获取高引用论文最终失败: {e}")
                return []
    
    return []


def get_relevence_paper(query, max_results=None, max_retries=None):
    """获取相关论文"""
    max_results = max_results or getattr(Config, 'MAX_PAPERS_PER_QUERY', 3)
    max_retries = max_retries or getattr(Config, 'SEMANTIC_SCHOLAR_MAX_RETRIES', 20)
    timeout = getattr(Config, 'SEMANTIC_SCHOLAR_TIMEOUT', 10)
    
    url = f"http://api.semanticscholar.org/graph/v1/paper/search"
    params = {"query": query, "fields": "title,abstract"}
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)    
            data = response.json()
            
            if 'data' in data:
                return data['data'][:max_results]
            else:
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"获取相关论文失败: {e}，{1}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                time.sleep(1)
                continue
            else:
                print(f"获取相关论文最终失败: {e}")
                return []
    
    return []


def get_prompt(template_name, locale="cn", **kwargs):
    """获取提示模板，根据locale添加语言输出指令"""
    if template_name not in PROMPT_TEMPLATES:
        raise ValueError(f"Template '{template_name}' is not found.")
        
    template = PROMPT_TEMPLATES[template_name]
    prompt = template.format(**kwargs)
    
    # 如果locale是cn，在prompt末尾添加中文输出指令
    if locale == "cn":
        chinese_instruction = "\n\nPlease provide your response in Chinese (中文)."
        prompt += chinese_instruction
    
    return prompt


def construct_paper(newest_paper, highly_cited_paper, relevence_paper):
    """构造论文信息"""
    paper = ""
    paper += "The latest paper:\n"
    for p in newest_paper:
        paper += f"Title: {p['title']}\nAbstract: {p['abstract']}\n\n"
    paper += "The highly cited paper:\n"
    for p in highly_cited_paper:
        paper += f"Title: {p['title']}\nAbstract: {p['abstract']}\n\n"
    paper += "The relevent paper:\n"
    for p in relevence_paper:
        paper += f"Title: {p['title']}\nAbstract: {p['abstract']}\n\n"
    return paper


class LLMClient:
    """LLM客户端 - 支持自定义API端点"""
    
    def __init__(self, llm: Optional[str] = None, provider: str = "custom", **kwargs):
        """
        初始化LLM客户端
        
        Args:
            llm: 模型名称
            provider: 提供商 ("custom")
            **kwargs: 其他参数
        """
        self.provider = provider
        self.config = Config
        
        # 设置模型 - 使用现有的配置名称，并提供默认值
        if provider == "custom":
            self.llm = llm or getattr(self.config, 'CUSTOM_MODEL', None) or 'deepseek-ai/DeepSeek-V3'
            self.endpoint = getattr(self.config, 'CUSTOM_API_ENDPOINT', None) or 'http://35.220.164.252:3888/v1'
            self.api_key = getattr(self.config, 'CUSTOM_API_KEY', None) or 'sk-B52cka26mugEd4P3EEDyIvMU2jlEabH37wuHz30KNy7825SZ'
        else:
            raise ValueError(f"不支持的提供商: {provider}")
        
        # 设置参数
        self.temperature = kwargs.get('temperature', 0.6)
        self.max_retries = kwargs.get('max_retries', 3)
        self.timeout = kwargs.get('timeout', getattr(self.config, 'LLM_REQUEST_TIMEOUT', 180))

    def _make_custom_api_call(self, prompt: str) -> str:
        """使用自定义API端点调用"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.llm,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "stream": False
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.endpoint}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"API超时，{wait_time}秒后重试... (尝试 {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"API调用超时，已重试{self.max_retries}次")
                    
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"API调用失败: {e}，{wait_time}秒后重试... (尝试 {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"API调用失败: {e}")

    def get_response(self, prompt: str, **kwargs) -> str:
        """获取LLM响应"""
        temperature = kwargs.get('temperature', self.temperature)
        max_retries = kwargs.get('max_retries', self.max_retries)
        
        # 临时更新参数
        original_temp = self.temperature
        original_retries = self.max_retries
        self.temperature = temperature
        self.max_retries = max_retries
        
        try:
            if self.provider == "custom":
                return self._make_custom_api_call(prompt)
            else:
                raise ValueError(f"不支持的提供商: {self.provider}")
        finally:
            # 恢复原始参数
            self.temperature = original_temp
            self.max_retries = original_retries

    def get_config_info(self) -> dict:
        """获取配置信息"""
        return {
            "provider": self.provider,
            "model": self.llm,
            "endpoint": self.endpoint,
            "temperature": self.temperature,
            "max_retries": self.max_retries,
            "timeout": self.timeout
        }
