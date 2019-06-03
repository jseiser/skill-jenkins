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

    async def _list_jobs(self, deployment):
        auth = aiohttp.BasicAuth(
            login=self.config["sites"][deployment]["username"],
            password=self.config["sites"][deployment]["password"],
        )
        timeout = aiohttp.ClientTimeout(total=10)
        api_url = f"{self.config['sites'][deployment]['url']}/api/json"

        async with aiohttp.ClientSession(auth=auth, timeout=timeout) as session:
            async with session.get(api_url) as resp:
                data = await resp.json()
                jobs = []
                for job in data["jobs"]:
                    if job["_class"] == "com.cloudbees.hudson.plugins.folder.Folder":
                        async with session.get(f"{job['url']}/api/json") as resp:
                            folder_data = await resp.json()
                            for folder_job in folder_data["jobs"]:
                                jobs.append(
                                    {
                                        "name": folder_job["name"],
                                        "url": folder_job["url"],
                                    }
                                )
                    else:
                        jobs.append({"name": job["name"], "url": job["url"]})
            return jobs

    async def _get_crumb(self, deployment):
        auth = aiohttp.BasicAuth(
            login=self.config["sites"][deployment]["username"],
            password=self.config["sites"][deployment]["password"],
        )
        timeout = aiohttp.ClientTimeout(total=10)
        api_url = f"{self.config['sites'][deployment]['url']}/job/{name}/crumbIssuer/api/json"
        async with aiohttp.ClientSession(auth=auth, timeout=timeout) as session:
            async with session.get(api_url) as resp:
                crumb = await resp.json()
        return crumb

    async def _get_job(self, deployment, name, folder=None):
        auth = aiohttp.BasicAuth(
            login=self.config["sites"][deployment]["username"],
            password=self.config["sites"][deployment]["password"],
        )
        timeout = aiohttp.ClientTimeout(total=10)
        if folder:
            api_url = f"{self.config['sites'][deployment]['url']}/job/{folder}/job/{name}/api/json"
        else:
            api_url = f"{self.config['sites'][deployment]['url']}/job/{name}/api/json"
        async with aiohttp.ClientSession(auth=auth, timeout=timeout) as session:
            async with session.get(api_url) as resp:
                data = await resp.json()
        return data

    async def _build_job(self, deployment, name, folder=None):
        crumb = job = await self._build_job(deployment, name, folder)
        if not crumb:
            retrn "Error Getting POST CRUMB"
        print(crumb)
        auth = aiohttp.BasicAuth(
            login=self.config["sites"][deployment]["username"],
            password=self.config["sites"][deployment]["password"],
        )
        timeout = aiohttp.ClientTimeout(total=10)
        if folder:
            api_url = f"{self.config['sites'][deployment]['url']}/job/{folder}/job/{name}/build"
        else:
            api_url = f"{self.config['sites'][deployment]['url']}/job/{name}/build"
        print(api_url)
        async with aiohttp.ClientSession(auth=auth, timeout=timeout) as session:
            async with session.post(api_url) as resp:
                print(resp.status)
                data = await resp.json()
                print(data)
        return data

    # Matching Functions

    @match_regex(r"^jenkins list deployments$")
    async def list_inventory(self, message):
        deployments = await self._get_deployments()

        await message.respond(f"{deployments}")

    @match_regex(r"^jenkins (?P<deployment>dev|prd) list jobs$")
    async def list_jobs(self, message):
        deployment = message.regex.group("deployment")
        jobs = await self._list_jobs(deployment)
        return_text = f"*{deployment} - Jobs*\n"
        for job in jobs:
            return_text = (
                f"{return_text}```\tName: {job['name']}\n\tURL: {job['url']}```\n"
            )

        await message.respond(f"{return_text}")

    @match_regex(r"^jenkins (?P<deployment>dev|prd) get job name: (?P<name>.*)$")
    async def get_job(self, message):
        deployment = message.regex.group("deployment")
        name = message.regex.group("name")
        job = await self._get_job(deployment, name)
        return_text = f"*{deployment} - {name}*\n"
        return_text = f"{return_text}```\tName: {job['name']}\n\tURL: {job['url']}\n\tHealth: {job['healthReport'][0]['description']}```\n"

        await message.respond(f"{return_text}")

    @match_regex(
        r"^jenkins (?P<deployment>dev|prd) get job name: (?P<name>.*) folder: (?P<folder>dev|stage)$"
    )
    async def get_job_folder(self, message):
        deployment = message.regex.group("deployment")
        name = message.regex.group("name")
        folder = message.regex.group("folder")
        job = await self._get_job(deployment, name, folder)
        return_text = f"*{deployment} - {name}*\n"
        return_text = f"{return_text}```\tName: {job['name']}\n\tURL: {job['url']}\n\tHealth: {job['healthReport'][0]['description']}```\n"

        await message.respond(f"{return_text}")

    @match_regex(r"^jenkins (?P<deployment>dev|prd) build job name: (?P<name>.*)$")
    async def build_job(self, message):
        deployment = message.regex.group("deployment")
        name = message.regex.group("name")
        job = await self._build_job(deployment, name)
        # return_text = f"*{deployment} - {name}*\n"
        # return_text = f"{return_text}```\tName: {job['name']}\n\tURL: {job['url']}\n\tHealth: {job['healthReport'][0]['description']}```\n"

        await message.respond(f"{job}")

    @match_regex(
        r"^jenkins (?P<deployment>dev|prd) build job name: (?P<name>.*) folder: (?P<folder>dev|stage)$"
    )
    async def build_job_folder(self, message):
        deployment = message.regex.group("deployment")
        name = message.regex.group("name")
        folder = message.regex.group("folder")
        job = await self._build_job(deployment, name, folder)
        # return_text = f"*{deployment} - {name}*\n"
        # return_text = f"{return_text}```\tName: {job['name']}\n\tURL: {job['url']}\n\tHealth: {job['healthReport'][0]['description']}```\n"

        await message.respond(f"{job}")
