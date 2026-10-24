"""026 reversible host/header-only schedule overlay; no device shader change."""
import build_nrd_vulkan as V

def replace(data,old,new,count=1):
    if data.count(old)!=count:raise ValueError('026 overlay expected occurrence: '+old[:80])
    return data.replace(old,new)

def header(raw):
    old='(spp==16||spp==64)';new='(spp==1||spp==4||spp==16||spp==64)'
    text=replace(raw.decode(),old,new,2)
    if text.replace(new,old)!=raw.decode():raise ValueError('026 header inverse')
    return text.encode()

def host(raw):
    text=raw.decode();changes=[
      ('u32 frame_index=iteration==1?1:0,seed=iteration==1?2654435769u:305419896u;auto common=m023::common(state.camera,frame_index,iteration!=1);','u32 frame_index=iteration,seed=305419896u+2654435769u*iteration;auto common=m023::common(state.camera,frame_index,iteration==0);'),
      ('<<(iteration!=1?"true":"false")','<<(iteration==0?"true":"false")'),
      ('for(u32 frame=0;frame<3;frame++)','for(u32 frame=0;frame<64;frame++)'),
      ('m001-nrd024-native-runtime/1','m001-nrd026-native-quality-runtime/1'),
      ('\\"frames\\":3,','\\"frames\\":64,')]
    for old,new in changes:text=replace(text,old,new)
    inverse=text
    for old,new in reversed(changes):inverse=replace(inverse,new,old)
    if inverse!=raw.decode():raise ValueError('026 host inverse')
    return text.encode()

def seed(i):
    if type(i) is not int or not 0<=i<64:raise ValueError('026 seed frame index')
    return (305419896+2654435769*i)&0xffffffff
