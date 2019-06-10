from opsdroid.skill import Skill
from opsdroid.matchers import match_regex

import aiohttp


class JenkinsSkill(Skill):
    async def _rest_call(self, deployment, api_url, call_method):
        auth = aiohttp.BasicAuth(
            login=self.config["sites"][deployment]["username"],
            password=self.config["sites"][deployment]["password"],
        )
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(auth=auth, timeout=timeout) as session:
            if call_method == "get":
                async with session.get(api_url) as resp:
                    data = await resp.json()
                    return data
            else:
                async with session.post(api_url) as resp:
                    data = await resp.json()
                    return data

    async def _get_deployments(self):
        sites = self.config["sites"]
        return_text = f"*Jenkins Deployments*\n"
        for site in sites:
            return_text = f"{return_text}```Deployment: {site} URL: {self.config['sites'][site]['url']}```\n"
        return return_text

    async def _list_jobs(self, deployment):
        api_url = f"{self.config['sites'][deployment]['url']}/api/json"

        data = await self._rest_call(deployment, api_url, "get")
        jobs = []
        for job in data["jobs"]:
            if job["_class"] == "com.cloudbees.hudson.plugins.folder.Folder":
                api_url = f"{job['url']}/api/json"
                folder_data = await self._rest_call(deployment, api_url, "get")
                for folder_job in folder_data["jobs"]:
                    jobs.append({"name": folder_job["name"], "url": folder_job["url"]})
            else:
                jobs.append({"name": job["name"], "url": job["url"]})
        return jobs

    async def _get_crumb(self, deployment):
        api_url = f"{self.config['sites'][deployment]['url']}/crumbIssuer/api/json"
        crumb = await self._rest_call(deployment, api_url, "get")
        return crumb

    async def _get_job(self, deployment, name, folder=None):
        if folder:
            api_url = f"{self.config['sites'][deployment]['url']}/job/{folder}/job/{name}/api/json"
        else:
            api_url = f"{self.config['sites'][deployment]['url']}/job/{name}/api/json"
        data = await self._rest_call(deployment, api_url, "get")
        return data

    async def _build_job(self, deployment, name, folder=None):
        crumb = await self._get_crumb(deployment)
        if not crumb:
            return "Error Getting POST CRUMB"

        if folder:
            api_url = f"{self.config['sites'][deployment]['url']}/job/{folder}/job/{name}/build"
        else:
            api_url = f"{self.config['sites'][deployment]['url']}/job/{name}/build"
        auth = aiohttp.BasicAuth(
            login=self.config["sites"][deployment]["username"],
            password=self.config["sites"][deployment]["password"],
        )
        timeout = aiohttp.ClientTimeout(total=10)
        headers = {crumb["crumbRequestField"]: crumb["crumb"]}
        async with aiohttp.ClientSession(
            auth=auth, timeout=timeout, headers=headers
        ) as session:
            async with session.post(api_url) as resp:
                return resp.status

    async def _get_help(self):
        return_text = f"*Help*\n"
        return_text = f"{return_text}```jenkins help - Returns This Help Screen```\n"
        return_text = f"{return_text}```jenkins list deployments - Returns Deployment keywords and urls```\n"
        return_text = f"{return_text}```jenkins <deployment> list jobs - Returns Name, Url of All Jobs in Deployment```\n"
        return_text = f"{return_text}```jenkins <deployment> get job name: <name> - Returns Name, URL and Health of Specific Job```\n"
        return_text = f"{return_text}```jenkins <deployment> build job name: <name> (folder: <folder>) - Builds Jenkins Pipeline by name, folder options.  Folder is required for jobs in a folder. like /dev/job_name```\n"
        return return_text

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
        return_text = f"*{deployment} - {name}*\n"
        return_text = f"{return_text}```\tLaunch Status: {job}```"

        await message.respond(f"{return_text}")

    @match_regex(
        r"^jenkins (?P<deployment>dev|prd) build job name: (?P<name>.*) folder: (?P<folder>dev|stage)$"
    )
    async def build_job_folder(self, message):
        deployment = message.regex.group("deployment")
        name = message.regex.group("name")
        folder = message.regex.group("folder")
        job = await self._build_job(deployment, name, folder)
        return_text = f"*{deployment} - {name}*\n"
        return_text = f"{return_text}```\tLaunch Status: {job}```"

        await message.respond(f"{return_text}")

    @match_regex(r"^jenkins help$")
    async def list_help(self, message):
        return_text = await self._get_help()

        await message.respond(f"{return_text}")
