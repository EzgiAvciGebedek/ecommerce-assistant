from google.adk.agents import LlmAgent
from google.adk.tools import agent_tool
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools import url_context

inventory_analyst_google_search_agent = LlmAgent(
  name='Inventory_Analyst_google_search_agent',
  model='gemini-2.5-flash',
  description=(
      'Agent specialized in performing Google searches.'
  ),
  sub_agents=[],
  instruction='Use the GoogleSearchTool to find information on the web.',
  tools=[
    GoogleSearchTool()
  ],
)
inventory_analyst_url_context_agent = LlmAgent(
  name='Inventory_Analyst_url_context_agent',
  model='gemini-2.5-flash',
  description=(
      'Agent specialized in fetching content from URLs.'
  ),
  sub_agents=[],
  instruction='Use the UrlContextTool to retrieve content from provided URLs.',
  tools=[
    url_context
  ],
)
inventory_analyst = LlmAgent(
  name='inventory_analyst',
  model='gemini-2.5-flash',
  description=(
      'Connects to the Merchant Center or Shopify API.'
  ),
  sub_agents=[],
  instruction='Flags products with \"Low Stock\" (e.g., <10 units) or \"Out of Stock\" status.',
  tools=[
    agent_tool.AgentTool(agent=inventory_analyst_google_search_agent),
    agent_tool.AgentTool(agent=inventory_analyst_url_context_agent)
  ],
)
search___display_specialist_google_search_agent = LlmAgent(
  name='Search___Display_Specialist_google_search_agent',
  model='gemini-2.5-flash',
  description=(
      'Agent specialized in performing Google searches.'
  ),
  sub_agents=[],
  instruction='Use the GoogleSearchTool to find information on the web.',
  tools=[
    GoogleSearchTool()
  ],
)
search___display_specialist_url_context_agent = LlmAgent(
  name='Search___Display_Specialist_url_context_agent',
  model='gemini-2.5-flash',
  description=(
      'Agent specialized in fetching content from URLs.'
  ),
  sub_agents=[],
  instruction='Use the UrlContextTool to retrieve content from provided URLs.',
  tools=[
    url_context
  ],
)
search__display_specialist = LlmAgent(
  name='search__display_specialist',
  model='gemini-2.5-flash',
  description=(
      'Analyzes Google Ads performance metrics (CTR, Impression Share, ROAS).'
  ),
  sub_agents=[],
  instruction='Identifies \"Rising Stars\" (high CTR/low spend) or \"Wasteful Spend\" (high spend/no sales).',
  tools=[
    agent_tool.AgentTool(agent=search___display_specialist_google_search_agent),
    agent_tool.AgentTool(agent=search___display_specialist_url_context_agent)
  ],
)
competitive_intelligence_agent_google_search_agent = LlmAgent(
  name='Competitive_Intelligence_Agent_google_search_agent',
  model='gemini-2.5-flash',
  description=(
      'Agent specialized in performing Google searches.'
  ),
  sub_agents=[],
  instruction='Use the GoogleSearchTool to find information on the web.',
  tools=[
    GoogleSearchTool()
  ],
)
competitive_intelligence_agent_url_context_agent = LlmAgent(
  name='Competitive_Intelligence_Agent_url_context_agent',
  model='gemini-2.5-flash',
  description=(
      'Agent specialized in fetching content from URLs.'
  ),
  sub_agents=[],
  instruction='Use the UrlContextTool to retrieve content from provided URLs.',
  tools=[
    url_context
  ],
)
competitive_intelligence_agent = LlmAgent(
  name='competitive_intelligence_agent',
  model='gemini-2.5-flash',
  description=(
      'Scrapes or uses APIs to monitor competitor ad copy.'
  ),
  sub_agents=[],
  instruction='Generates improved Headline/Description suggestions using LLM creative capabilities.',
  tools=[
    agent_tool.AgentTool(agent=competitive_intelligence_agent_google_search_agent),
    agent_tool.AgentTool(agent=competitive_intelligence_agent_url_context_agent)
  ],
)
ecommerce_assistant_google_search_agent = LlmAgent(
  name='Ecommerce_Assistant_google_search_agent',
  model='gemini-2.5-flash',
  description=(
      'Agent specialized in performing Google searches.'
  ),
  sub_agents=[],
  instruction='Use the GoogleSearchTool to find information on the web.',
  tools=[
    GoogleSearchTool()
  ],
)
ecommerce_assistant_url_context_agent = LlmAgent(
  name='Ecommerce_Assistant_url_context_agent',
  model='gemini-2.5-flash',
  description=(
      'Agent specialized in fetching content from URLs.'
  ),
  sub_agents=[],
  instruction='Use the UrlContextTool to retrieve content from provided URLs.',
  tools=[
    url_context
  ],
)
root_agent = LlmAgent(
  name='Ecommerce_Assistant',
  model='gemini-2.5-flash',
  description=(
      'Agent helps to control and allocate the budget among campaigns'
  ),
  sub_agents=[inventory_analyst, search__display_specialist, competitive_intelligence_agent],
  instruction='If main agent reports a high-impact opportunity, summarize the data, send a Slack interactive message, and wait for a True response before triggering the execution tool.',
  tools=[
    agent_tool.AgentTool(agent=ecommerce_assistant_google_search_agent),
    agent_tool.AgentTool(agent=ecommerce_assistant_url_context_agent)
  ],
)