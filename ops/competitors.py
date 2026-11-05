import sys, json, re, os
sys.argv=['x']; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import yt
import os; OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'competitors','')
groups = {
 "rumi": ["Rumi poetry", "Rumi quotes Shams Tabrizi", "Sufi poetry Persian"],
 "history": ["Persian history podcast", "medieval Islamic history storytelling", "history of Iran documentary"],
 "kids": ["moral stories for kids animated fables", "Panchatantra stories for kids", "bedtime stories for kids animated"],
}
def dur(s):
    m = re.match(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', s or '')
    if not m: return 0
    d,h,mi,se=[int(x or 0) for x in m.groups()]; return d*86400+h*3600+mi*60+se
res = {}
for g, qs in groups.items():
    chans = {}
    for q in qs:
        r = yt.call(yt.API+'search', {'part':'snippet','q':q,'type':'channel','maxResults':10,'relevanceLanguage':'en'})
        for it in r.get('items', []): chans[it['snippet']['channelId']] = it['snippet']['title']
    ids = list(chans)
    st = yt.call(yt.API+'channels', {'part':'snippet,statistics,contentDetails','id':','.join(ids[:50])})['items']
    st = [c for c in st if not c['statistics'].get('hiddenSubscriberCount')]
    st.sort(key=lambda c: int(c['statistics'].get('subscriberCount',0)), reverse=True)
    out = []
    for c in st[:6]:
        up = c['contentDetails']['relatedPlaylists']['uploads']
        try:
            vids = [i['contentDetails']['videoId'] for i in yt.call(yt.API+'playlistItems', {'part':'contentDetails','playlistId':up,'maxResults':50})['items']]
        except SystemExit: vids=[]
        vs = yt.call(yt.API+'videos', {'part':'snippet,statistics,contentDetails','id':','.join(vids)})['items'] if vids else []
        rows = [{'t':v['snippet']['title'],'views':int(v['statistics'].get('viewCount',0)),'dur':dur(v['contentDetails']['duration']),'date':v['snippet']['publishedAt'][:10]} for v in vs]
        rows.sort(key=lambda r:r['views'], reverse=True)
        shorts = [r for r in rows if r['dur']<=60]; longs=[r for r in rows if r['dur']>60]
        out.append({'name':c['snippet']['title'],'id':c['id'],'country':c['snippet'].get('country'),'subs':int(c['statistics'].get('subscriberCount',0)),
                    'views':int(c['statistics'].get('viewCount',0)),'videos':int(c['statistics'].get('videoCount',0)),'created':c['snippet']['publishedAt'][:10],
                    'recent50':{'n':len(rows),'shorts':len(shorts),'median_short':sorted([r['views'] for r in shorts])[len(shorts)//2] if shorts else None,
                                'median_long':sorted([r['views'] for r in longs])[len(longs)//2] if longs else None,
                                'avg_long_min':round(sum(r['dur'] for r in longs)/len(longs)/60,1) if longs else None,
                                'first':rows and min(r['date'] for r in rows),'last':rows and max(r['date'] for r in rows)},
                    'top':rows[:6]})
    res[g]=out
json.dump(res, open(OUT+'comp.json','w'), ensure_ascii=False, indent=1)
for g,o in res.items():
    print('=====',g)
    for c in o:
        print(f"{c['name'][:40]:40} subs={c['subs']:>9} vids={c['videos']:>5} since {c['created']} | recent50 shorts={c['recent50']['shorts']} medS={c['recent50']['median_short']} medL={c['recent50']['median_long']} avgL={c['recent50']['avg_long_min']}m {c['recent50']['first']}..{c['recent50']['last']}")
        for r in c['top'][:4]: print(f"     {r['views']:>9} {r['dur']:>5}s {r['t'][:80]}")
