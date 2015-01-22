import requests
import json
import database
from datetime import datetime
import sys

#paging parameters
#Github API default: 100 per page (https://developer.github.com/v3/search/)
per_page = 100


def get_basic_info(repo):
    req = requests.get('https://api.github.com/repos/' + repo,auth=(user,pwd))
    data = json.loads(req.text)
    stars = data['stargazers_count']
    watchers = data['subscribers_count']
    forks = data['forks_count']
    size = data['size']
    return (stars, watchers, forks, size)


def get_pullrequest(repo):
    pulls = 0
    page = 1
    state = "all" #default is 'open', but we want to get all open and closed pull requests
    while True:
        parameter = {'page':page,'per_page':per_page,'state':state}
        req = requests.get('https://api.github.com/repos/'+repo+'/pulls',params=parameter,auth=(user,pwd))
        data = json.loads(req.text)
        pulls += len(data)
        if len(data) < per_page:
            break
        page += 1
    return pulls

#labels are too different from repo to repo. Maybe we need to simply count total # of bugs and # of closed bugs
#another possible quality metric can be issue close duration?
#return (total bugs, closed bugs, average fix duration for closed bugs)
def get_bugs(repo):
    total_bugs = 0
    duration = [] #minutes
    page = 1
    state = "all"
    while True:
        parameter = {'page':page,'per_page':per_page,'state':state}
        req = requests.get('https://api.github.com/repos/'+repo+'/issues',params=parameter,auth=(user,pwd))
        data = json.loads(req.text)
        total_bugs += len(data)
        for i in range(len(data)):
            if data[i]['state'] == 'closed':
                create_at = datetime.strptime(data[i]['created_at'],'%Y-%m-%dT%H:%M:%SZ')
                if data[i]['closed_at'] is not None:
                    closed_at = datetime.strptime(data[i]['closed_at'],'%Y-%m-%dT%H:%M:%SZ')
                elif data[i]['updated_at'] is not None:
                    #if closed_at is None, try last update time
                    closed_at = datetime.strptime(data[i]['updated_at'],'%Y-%m-%dT%H:%M:%SZ')
                else:
                    #in this case, ignore this bug
                    continue
                close_duration = divmod((closed_at - create_at).total_seconds(),60)[0]
                duration.append(close_duration)
        if len(data) < per_page:
            break
        page += 1
    avg_duration = round(sum(duration)/len(duration),2) if len(duration) > 0 else -1
    return (total_bugs,len(duration),avg_duration)


#get core contributors and temp contributors' percentage
#core_ratio is the percentage of all commits
def get_contributors(repo, core_ratio):
    contributors = {} #<username, # of commits>
    page = 1
    anon = 1 #include anonymous contributors
    anon_user = 1
    while True:
        parameter = {'page':page,'per_page':per_page,'anon':anon}
        req = requests.get('https://api.github.com/repos/' + repo + '/contributors',params=parameter,auth=(user,pwd))
        data = json.loads(req.text)
        for i in range(len(data)):
            if 'login' in data[i]:
                name = data[i]['login']
            else:
                name = 'anonymous_user' + str(anon_user)
                anon_user += 1
            commits = data[i]['contributions']
            contributors[name] = commits
        if len(data) < per_page:
            break
        page += 1
    contributors = sorted(contributors.items(), key=lambda x: x[1], reverse=True)
    all_commits = sum([x[1] for x in contributors])
    major_commits = all_commits * core_ratio
    sum_commits = 0
    core_contributors = []
    for c in contributors:
        core_contributors.append(c[0])
        sum_commits += c[1]
        if sum_commits > major_commits:
            break
    noncore_contributors = [x[0] for x in contributors if x[0] not in core_contributors]
    noncore_percent = round(len(noncore_contributors)/len(contributors),2)
    return (len(contributors),core_contributors,noncore_percent)


#get the average followers for core members
def get_avg_core_followers(core_contributors):
    followers = 0
    count = len(core_contributors)
    for cc in core_contributors:
        if cc.startswith('anonymous_user'):
            count -= 1
            continue

        f = database.query_user(cc)
        if f is not None:
            #user already in database
            followers += f
            continue

        page = 1
        follow = 0
        while True:
            parameter = {'page':page,'per_page':per_page}
            req = requests.get('https://api.github.com/users/'+cc+'/followers',params=parameter,auth=(user,pwd))
            data = json.loads(req.text)
            follow += len(data)
            if len(data) < per_page:
                break
            page += 1
        database.insert_user(cc,follow)
        followers += follow
    #if count == 0, then probably the core members are anonymous. We skip such repositories
    return round(followers / count, 2) if count > 0 else -1

#get the commit ratio of non-core contributors
def get_noncore_contributions(repo, noncore_contributors):
    allcommits = 0
    page = 1
    while True:
        parameter = {'page':page,'per_page':per_page}
        req = requests.get('https://api.github.com/repos/' + repo + '/commits',params=parameter,auth=(user,pwd))
        data = json.loads(req.text)
        allcommits += len(data)
        if len(data) < per_page:
            break
        page += 1
    noncore_commits = sum([nc[1] for nc in noncore_contributors])
    return round(noncore_commits / allcommits, 2)


#get the N most popular github repositories
def get_popular_repo(N, language):
    repo_list = []
    page = 1
    lan = 'language:'+language
    while True:
        parameter = {'page':page,'per_page':per_page,'q':lan,'sort':'stars','order':'desc'}
        req = requests.get('https://api.github.com/search/repositories',params=parameter,auth=(user, pwd))
        data = json.loads(req.text)
        items = data['items']
        for i in range(len(items)):
            repo_list.append(items[i]['full_name'])
            if len(repo_list) == N:
                return repo_list
        page += 1

if __name__ == "__main__":
    args = sys.argv
    user, pwd = args[0], args[1]
    #Search the top N repo of the top 5 language

    N = 100 #TODO: test right now
    #Source: http://redmonk.com/sogrady/2014/01/22/language-rankings-1-14/
    #Specify one language in ['javascript','java','php','c#','python']
    lan = "python"
    repositories = get_popular_repo(N, lan)

    repo_with_zero_bugs = 0
    #Currently we treat the top 1/5 as core members (sorted by # of commits)
    core_ratio = 0.8
    for repo in repositories:
        if database.has_repo(repo):
            print(repo + ' already exists')
            continue

        #(total bugs, closed bugs, average fix duration)
        bugs = get_bugs(repo)
        #bugs might be zero if the repo is not hosted in Github (e.g., nathanmarz/storm). Ignore these repos
        if bugs[0] == 0 or bugs[1] == 0:
            repo_with_zero_bugs += 1
            print(repo + ' has 0 issues')
            continue

        print(repo + ' starts ...')
        #(team size, core members, noncore members' percentage)
        team = get_contributors(repo, core_ratio)
        avg_core_followers = get_avg_core_followers(team[1])
        if avg_core_followers == -1:
            print(repo + ' skip for anonymous core contributors')
            continue
        #(stars, watchers, forks, size)
        basic_info = get_basic_info(repo)
        pullreq = get_pullrequest(repo)
        #noncore_commit_ratio = get_noncore_contributions(repo, team[2])
        #TODO from wagerfield/parallax, the core members are those who made the top 80% commits. NonCoreCommitRatio column is now the percentage of noncore members among all contributors
        database.insert(repo,lan,basic_info[0],basic_info[1],basic_info[2],pullreq,avg_core_followers,team[2],basic_info[3],team[0],bugs[0],bugs[1],bugs[2])
        print(repo + ' done.')

