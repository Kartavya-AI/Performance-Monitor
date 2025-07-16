import yaml
import os
from pathlib import Path
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from crewai_tools import SerperDevTool

from src.performance_monitor.tools.custom_tool import SiteMapTool, BrowserTool, ScraperTool

class PerformanceMonitorCrew:
    def __init__(self, url: str):
        self.url = url
        config_path = Path(__file__).parent / 'config'
        self.agents_config = self._load_yaml(config_path / 'agents.yaml')
        self.tasks_config = self._load_yaml(config_path / 'tasks.yaml')
        self.llm = self._get_llm()

    def _load_yaml(self, path: Path):
        with open(path, 'r') as file:
            return yaml.safe_load(file)

    def _get_llm(self):
        """Initialize the appropriate LLM based on environment variables."""
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()  # Default to gemini
        
        if provider == "gemini":
            model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro")
            google_api_key = os.getenv("GOOGLE_API_KEY")
            
            if not google_api_key:
                raise ValueError("GOOGLE_API_KEY environment variable is required for Gemini")
            
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=google_api_key,
                temperature=0.1,
                convert_system_message_to_human=True
            )
        elif provider == "openai":
            model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")
            openai_api_key = os.getenv("OPENAI_API_KEY")
            
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI")
            
            return ChatOpenAI(
                model=model_name,
                openai_api_key=openai_api_key,
                temperature=0.1
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}. Use 'gemini' or 'openai'")

    def _get_tools(self):
        """Get available tools including optional Serper tool."""
        tools = {
            'site_map': SiteMapTool(),
            'browser': BrowserTool(),
            'scraper': ScraperTool()
        }
        
        # Add Serper tool if API key is available
        if os.getenv("SERPER_API_KEY"):
            tools['search'] = SerperDevTool()
        
        return tools

    def run(self):
        tools = self._get_tools()
        
        # Create agents with the configured LLM
        # Remove 'tools' from config if it exists to avoid conflicts
        site_crawler_config = self.agents_config['site_crawler'].copy()
        site_crawler_config.pop('tools', None)
        site_crawler_agent = Agent(
            **site_crawler_config,
            tools=[tools['site_map']],
            llm=self.llm
        )
        
        performance_analyst_config = self.agents_config['performance_analyst'].copy()
        performance_analyst_config.pop('tools', None)
        performance_analyst_agent = Agent(
            **performance_analyst_config,
            tools=[tools['browser']],
            llm=self.llm
        )
        
        # Add search tool to SEO auditor if available
        seo_tools = [tools['scraper']]
        if 'search' in tools:
            seo_tools.append(tools['search'])
        
        seo_auditor_config = self.agents_config['seo_accessibility_auditor'].copy()
        seo_auditor_config.pop('tools', None)
        seo_auditor_agent = Agent(
            **seo_auditor_config,
            tools=seo_tools,
            llm=self.llm
        )
        
        report_synthesizer_config = self.agents_config['report_synthesizer'].copy()
        report_synthesizer_config.pop('tools', None)
        report_synthesizer_agent = Agent(
            **report_synthesizer_config,
            llm=self.llm
        )
        
        # Create tasks
        crawl_task = Task(
            **self.tasks_config['crawl_website'],
            agent=site_crawler_agent
        )
        
        performance_task = Task(
            **self.tasks_config['analyze_performance'],
            agent=performance_analyst_agent,
            context=[crawl_task]
        )
        
        seo_task = Task(
            **self.tasks_config['audit_seo_and_accessibility'],
            agent=seo_auditor_agent,
            context=[crawl_task]
        )
        
        report_task = Task(
            **self.tasks_config['compile_final_report'],
            agent=report_synthesizer_agent,
            context=[performance_task, seo_task]
        )

        # Create and run crew
        crew = Crew(
            agents=[site_crawler_agent, performance_analyst_agent, seo_auditor_agent, report_synthesizer_agent],
            tasks=[crawl_task, performance_task, seo_task, report_task],
            process=Process.sequential,
            verbose=True,
            memory=True
        )

        result = crew.kickoff(inputs={'url': self.url})
        return result