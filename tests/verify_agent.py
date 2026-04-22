from agent_starter_pack.cli.utils.template import get_available_agents

agents = get_available_agents()
for agent in agents.values():
    if agent["name"] == "super_duper_agent":
        print("SuperDuperAgent found!")
        exit(0)

print("SuperDuperAgent not found.")
exit(1)
