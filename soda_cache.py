# Author: Kerwin
"""Read-only LMDB v2 / MessagePack record decoder for Soda's existing cache.

Only primitive data is decoded: no pickle, JavaScript execution, or player hooks.
Unknown file/extension formats are rejected rather than guessed.
"""
import mmap
import struct
from pathlib import Path


class Records:
    def __init__(self, data):
        self.data=data;self.offset=0;self.structures={};self.depth=0
    def take(self,count):
        if count<0 or self.offset+count>len(self.data):raise ValueError('缓存记录不完整')
        result=self.data[self.offset:self.offset+count];self.offset+=count;return result
    def number(self,fmt):return struct.unpack(fmt,self.take(struct.calcsize(fmt)))[0]
    def read(self):
        self.depth+=1
        if self.depth>80:raise ValueError('缓存记录嵌套过深')
        try:return self.value()
        finally:self.depth-=1
    def array(self,n):
        if n>100000:raise ValueError('缓存数组过大')
        return [self.read() for _ in range(n)]
    def mapping(self,n):
        if n>100000:raise ValueError('缓存对象过大')
        return {self.read():self.read() for _ in range(n)}
    def extension(self,n):
        kind=self.number('b');payload=self.take(n)
        if kind==0x72 and n in (1,2):
            identifier=payload[0] if n==1 else payload[0]+(payload[1]<<5)
            keys=self.read()
            if not isinstance(keys,list) or any(not isinstance(k,str) for k in keys):raise ValueError('非法缓存结构')
            self.structures[identifier]=keys
            return {key:self.read() for key in keys}
        if kind==0 and n==1:return None
        if kind==-1:return payload  # timestamps are irrelevant to lyric content
        raise ValueError('不支持的缓存扩展 '+str(kind))
    def value(self):
        tag=self.number('B')
        if tag<=0x7f:
            if tag in self.structures:return {key:self.read() for key in self.structures[tag]}
            return tag
        if tag>=0xe0:return tag-256
        if 0xa0<=tag<=0xbf:return self.take(tag&31).decode('utf-8')
        if 0x90<=tag<=0x9f:return self.array(tag&15)
        if 0x80<=tag<=0x8f:return self.mapping(tag&15)
        if tag==0xc0:return None
        if tag in (0xc2,0xc3):return tag==0xc3
        formats={0xca:'>f',0xcb:'>d',0xcc:'>B',0xcd:'>H',0xce:'>I',0xcf:'>Q',0xd0:'>b',0xd1:'>h',0xd2:'>i',0xd3:'>q'}
        if tag in formats:return self.number(formats[tag])
        lengths={0xc4:'>B',0xc5:'>H',0xc6:'>I',0xd9:'>B',0xda:'>H',0xdb:'>I',0xdc:'>H',0xdd:'>I',0xde:'>H',0xdf:'>I'}
        if tag in lengths:
            count=self.number(lengths[tag])
            if tag in (0xdc,0xdd):return self.array(count)
            if tag in (0xde,0xdf):return self.mapping(count)
            data=self.take(count)
            return data.decode('utf-8') if tag in (0xd9,0xda,0xdb) else data
        if 0xd4<=tag<=0xd8:return self.extension(1<<(tag-0xd4))
        if tag in (0xc7,0xc8,0xc9):return self.extension(self.number({0xc7:'>B',0xc8:'>H',0xc9:'>I'}[tag]))
        raise ValueError('不支持的缓存编码 '+hex(tag))


def records(path):
    """Traverse only the newest committed main DB tree; never alter LMDB locks."""
    with Path(path).open('rb') as file, mmap.mmap(file.fileno(),0,access=mmap.ACCESS_READ) as data:
        page_size=4096
        if len(data)<page_size*2:raise ValueError('缓存数据库过小')
        metas=[]
        for base in (0,page_size):
            if struct.unpack_from('<II',data,base+24)!=(0xbeefc0de,2):raise ValueError('不支持的汽水缓存版本')
            metas.append((struct.unpack_from('<Q',data,base+152)[0],struct.unpack_from('<Q',data,base+136)[0]))
        root=max(metas)[1];visited=set()
        def walk(page,depth=0):
            if page in visited or depth>24 or page*page_size+24>len(data):raise ValueError('缓存页链异常')
            visited.add(page);base=page*page_size
            flags,lower=struct.unpack_from('<HH',data,base+18)
            if flags not in (1,2) or lower>page_size-24 or lower%2:raise ValueError('缓存页结构异常')
            for index in range(lower//2):
                relative=struct.unpack_from('<H',data,base+24+index*2)[0]
                node=base+24+relative
                if node+8>base+page_size:raise ValueError('缓存节点越界')
                size,node_flags,key_length=struct.unpack_from('<IHH',data,node)
                start=node+8+key_length
                if flags==1:
                    yield from walk(size | (node_flags<<32),depth+1)
                else:
                    if size>16*1024*1024 or start>base+page_size:continue
                    if node_flags&1:
                        page_number=struct.unpack_from('<Q',data,start)[0]
                        start=page_number*page_size+24
                    if start+size>len(data):continue
                    yield bytes(data[start:start+size])
        for payload in walk(root):
            try:
                value=Records(payload).read()
                if isinstance(value,dict):yield value
            except (ValueError,UnicodeError,struct.error,TypeError,KeyError):continue
