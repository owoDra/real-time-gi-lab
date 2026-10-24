"""028 exact reversible one-setting host/API overlays; no SDK/shader edit."""
import nrd_quality_overlay as Q

SETTING=('nrd::RelaxSettings settings{};',
         'nrd::RelaxSettings settings{};settings.diffusePrepassBlurRadius=0.0f;')

def apply(raw, changes):
    text=raw.decode()
    for old,new in changes:text=Q.replace(text,old,new)
    inverse=text
    for old,new in reversed(changes):inverse=Q.replace(inverse,new,old)
    if inverse!=raw.decode():raise ValueError('028 inverse overlay failed')
    return text.encode()

def host(raw):
    return apply(Q.host(raw),[SETTING,('m001-nrd026-native-quality-runtime/1','m001-nrd028-native-quality-runtime/1')])

def probe(raw):
    return apply(raw,[SETTING,('m001-nrd023-instance/1','m001-nrd028-instance/1'),
        ('m001-nrd023-real-sdk-cpu-probe/1','m001-nrd028-real-sdk-cpu-probe/1'),
        ('default_settings','configured_settings')])

header=Q.header
seed=Q.seed
