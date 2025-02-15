class Community:
    def __init__(self):
        self.agents = []

    def add_agent(self, agent):
        self.agents.append(agent)

    def generate_interactions(self):
        interactions = []
        for agent in self.agents:
            for other_agent in self.agents:
                if agent != other_agent:
                    interaction = agent.interact(other_agent)
                    interactions.append(interaction)
        return interactions

    def community_metrics(self):
        total_energy = sum(agent.energy for agent in self.agents)
        total_ct_balance = sum(agent.ct_balance for agent in self.agents)
        return total_energy, total_ct_balance