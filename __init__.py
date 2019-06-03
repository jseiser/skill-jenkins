from opsdroid.skill import Skill
from opsdroid.matchers import match_regex

import aiohttp


class JenkinsSkill(Skill):
    async def _get_deployments(self):
        sites = self.config["sites"]
        return_text = f"*Jenkins Deployments*\n"
        for site in sites:
            return_text = f"{return_text}```Deployment: {site} URL: {self.config['sites'][site]['url']}```\n"
        return return_text

    async def _get_jobs(self, deployment):
        auth = aiohttp.BasicAuth(
            login=self.config["sites"][deployment]["username"],
            password=self.config["sites"][deployment]["password"],
        )
        timeout = aiohttp.ClientTimeout(total=60)
        api_url = f"{self.config['sites'][deployment]['url']}/api/json"

        async with aiohttp.ClientSession(auth=auth, timeout=timeout) as session:
            async with session.get(api_url) as resp:
                data = await resp.json()
                jobs = {}
                for job in data["jobs"]:
                    print(job)
                    if job["_class"] == "com.cloudbees.hudson.plugins.folder.Folder":
                        print(job["url"])
                        async with session.get(job["url"]) as resp:
                            folder_data = await resp.json()
                            for folder_job in folder_data["jobs"]:
                                print(folder_job)
                                jobs.update(
                                    {
                                        "name": folder_job["name"],
                                        "url": folder_job["url"],
                                    }
                                )
                    else:
                        jobs.update({"name": job["name"], "url": job["url"]})
            return jobs

    # Matching Functions

    @match_regex(r"^jenkins list deployments$")
    async def list_inventory(self, message):
        deployments = await self._get_deployments()

        await message.respond(f"{deployments}")

    @match_regex(r"^jenkins (?P<deployment>\w+-\w+|\w+) list jobs$")
    async def get_jobs(self, message):
        deployment = message.regex.group("deployment")
        jobs = await self._get_jobs(deployment)

        await message.respond(f"{jobs}")
