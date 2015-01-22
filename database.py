import pymysql

conn = pymysql.connect(host='test', port=3306, user='test', passwd='test', db='github', charset='utf8')

#create table
def create_repo_transparency():
    #TODO rename the noncorecommitratio column to noncoreratio
    sql = 'create table github.repo_transparency (Repo varchar(100),Language varchar(15),Stars int,Watchers int,Forks int,Pullrequests int,AvgCoreFollowers int,NonCoreCommitRatio float,RepoSize int,TeamSize int,AllBugs int,ClosedBugs int,AvgFixDuration float)'
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.close()

#create user table
def create_user():
    sql = 'create table github.user (User varchar(100),Followers int)'
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.close()

def query_user(username):
    sql = 'select Followers from github.user where User=\"' + username + '\"'
    cur = conn.cursor()
    cur.execute(sql)
    res = cur.fetchall()
    followers = None
    if len(res) == 1:
        followers = int(res[0][0])
    cur.close()
    return followers

def insert_user(username,followers):
    sql = 'insert into github.user values(\"' + username + '\",' + str(followers) + ')'
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.close()


#insert repositories to be analyzed
def insert(repo,lang,stars,watchers,forks,pullreqs,avg_core_followers,noncore_commit_ratio,repo_size,team_size,total_bugs,closed_bugs,avg_fix_duration):
    sql = 'insert into github.repo_transparency values(\"' + repo + '\",\"' + lang + '\",' + str(stars) + ',' + str(watchers) + ',' + str(forks) + ',' + str(pullreqs) + ',' + str(avg_core_followers) + ',' + str(noncore_commit_ratio) + ',' + str(repo_size) + ',' + str(team_size) + ',' + str(total_bugs) + ',' + str(closed_bugs) + ',' + str(avg_fix_duration) + ')'
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.close()

def has_repo(repo):
    sql = 'select Repo from github.repo_transparency where Repo=\"' + repo + '\"'
    cur = conn.cursor()
    cur.execute(sql)
    res = cur.fetchall()
    hasRepo = True if len(res) == 1 else False
    cur.close()
    return hasRepo
