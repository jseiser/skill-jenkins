from opsdroid.skill import Skill
from opsdroid.matchers import match_regex

import aiohttp


class JenkinsSkill(Skill):
    # being Matching Functions

    async def _get_deployments(self):
        sites = self.config["sites"]
        return_text = f"*Jenkins Deployments*\n"
        for site in sites:
            return_text = f"{return_text}```Deployment: {site} URL: {self.config['sites'][site]['url']}```\n"
        return return_text

    @match_regex(r"^jenkins list deployments$")
    async def list_inventory(self, message):
        deployments = await self._get_deployments()

        await message.respond(f"{deployments}")
