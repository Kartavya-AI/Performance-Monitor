import sys
from dotenv import load_dotenv
load_dotenv()
from src.performance_monitor.crew import PerformanceMonitorCrew

def run(url: str):
    crew = PerformanceMonitorCrew(url)
    crew_result = crew.run()
    return crew_result

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
        print(f"🚀 Starting analysis for: {target_url}")
        result = run(target_url)
        print("\n\n🏁 Analysis Complete!")
        print(result)
    else:
        print("Please provide a URL to analyze.")
        print("Example: python src/performance_monitor/main.py https://streamlit.io")