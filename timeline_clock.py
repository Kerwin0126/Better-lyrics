# Author: Kerwin
"""Project sparse Soda SMTC anchors onto a monotonic local playback clock."""

class SodaTimeline:
    def __init__(self):
        self.identity=None
        self.received=None
        self.token=None
        self.raw=0.0
        self.base=0.0
        self.updated=0.0
        self.rate=1.0
        self.state='paused'
        self.revision=0
        self.duration=0

    def position(self,now):
        advance=max(0,now-self.updated)*1000*self.rate if self.state=='playing' else 0
        return max(0,min(self.base+advance,self.duration or self.base+advance))

    def project(self,data,received):
        result=dict(data)
        if self.received==received:
            result.update(position_ms=self.position(received),clock_revision=self.revision,
                          timeline_position_ms=float(data['position_ms']),precision='steady_timeline')
            return result
        raw=float(data['position_ms'])
        stamp=float(data.get('timeline_updated_ms',0))
        age=float(data.get('timeline_age_ms',0))
        identity,state=data['identity'],data['state']
        duration=float(data.get('duration_ms',0))
        token=(raw,stamp)
        changed=identity!=self.identity or abs(duration-self.duration)>2500
        previous=self.position(received)
        # Only a plausible timestamp may establish a first anchor. An old
        # paused timestamp briefly reused on resume must not jump to song end.
        lag=age if 0<=age<=duration and raw+age<=duration+2000 else 0
        candidate=raw+(lag if state=='playing' else 0)
        stale=not changed and self.token is not None and stamp<self.token[1]
        if changed:
            self.base,self.rate=candidate,1.0
            self.revision+=1
        elif stale:
            self.base=previous
        elif state!=self.state and raw==self.raw:
            self.base,self.rate=previous,1.0
        elif token==self.token:
            # A timeline is an anchor, not a fresh position at every poll.
            # Keep advancing for as long as playback and reader samples are live.
            self.base=previous
            if state!=self.state:self.rate=1.0
        elif state=='paused':
            self.base,self.rate=raw,1.0
        else:
            error=candidate-previous
            if raw<self.raw-100 or abs(error)>1800:
                self.base,self.rate=candidate,1.0
                self.revision+=1
            else:
                # Correct ordinary anchor jitter through speed, never rewind.
                self.base=previous
                self.rate=1+max(-.15,min(.15,error/3000))
        self.updated=received
        self.state=state
        self.identity,self.received,self.duration=identity,received,duration
        if not stale:self.token,self.raw=token,raw
        result.update(position_ms=self.position(received),precision='steady_timeline',
                      timeline_position_ms=raw,clock_revision=self.revision)
        return result
