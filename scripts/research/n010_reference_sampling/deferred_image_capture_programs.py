"""Plan 054 isolated CPU serialization overlay; assembly never dispatches a GPU."""
import json
import os
from pathlib import Path

import bulk_pfm_capture_programs as B

HERE, ROOT, RESULTS = B.HERE, B.ROOT, B.RESULTS
PLAN = RESULTS.parent/'experiments/054-prospective-deferred-image-serialization.md'
FIXTURE = ROOT/'out/research/n010-comparison-readiness/deferred-image-calibration-build-v1'
OUTPUT = RESULTS/'184-deferred-image-calibration-fixture-build.json'

SPOOL = r'''
// Calibration-only CPU RGBA storage. GPU workloads and readbacks are unchanged.
struct N010DeferredImages {
    struct Entry { fs::path directory; uint32_t width, height; std::vector<float> rgba; bool root; };
    static constexpr size_t limit=256U*1024U*1024U;
    std::vector<Entry> entries;
    size_t retained_bytes{}, peak_bytes{}, retained_count{};
    explicit N010DeferredImages(size_t count) {
        if(count>256)throw std::runtime_error("deferred image count exceeds bound");
        entries.reserve(count);
    }
    void retain(fs::path directory,uint32_t width,uint32_t height,std::vector<float>&& rgba,bool root=false) {
        const size_t bytes=rgba.capacity()*sizeof(float);
        if(entries.size()>=256 || rgba.size()!=size_t(width)*height*4U || bytes>limit-retained_bytes)
            throw std::runtime_error("deferred CPU RGBA storage bound/shape failure");
        entries.push_back({std::move(directory),width,height,std::move(rgba),root});
        retained_bytes+=bytes; if(retained_bytes>peak_bytes)peak_bytes=retained_bytes;
        ++retained_count;
    }
    template<class Writer> void flush(const fs::path& out,Writer writer) {
        for(auto& entry:entries) {
            writer(entry);
            retained_bytes-=entry.rgba.capacity()*sizeof(float);
            std::vector<float>().swap(entry.rgba);
        }
        entries.clear();
        if(retained_bytes)throw std::runtime_error("deferred image payload not released");
        std::ofstream record(out/"deferred-image-serialization.json");
        record<<"{\"schema\":\"n010-deferred-image-serialization/1\",\"complete\":true,"
              <<"\"retained_frames\":"<<retained_count<<",\"written_frames\":"<<retained_count
              <<",\"rgba_capacity_limit_bytes\":"<<limit<<",\"rgba_capacity_peak_bytes\":"<<peak_bytes
              <<",\"rgba_capacity_bytes_after_flush\":"<<retained_bytes
              <<",\"scope\":\"CPU RGBA vector capacities only; other CPU storage and Vulkan allocations separate\"}\n";
        if(!record)throw std::runtime_error("deferred image receipt write failed");
    }
};
'''


def pairs():
    return {
        'capture':[
            ('int main(int argc,char** argv) {', SPOOL+'\nint main(int argc,char** argv) {'),
            ('            for(size_t index=0;index<doses.size();++index) {',
             '            N010DeferredImages deferred(doses.size());\n            for(size_t index=0;index<doses.size();++index) {'),
            ('                const auto image=runtime.renderer_readback();',
             '                auto image=runtime.renderer_readback();'),
            ('''                for(uint32_t component=0;component<3;++component) {
                    std::vector<float> values(size_t(image.width)*image.height);
                    for(size_t px=0;px<values.size();++px)values[px]=image.image_rgba[4*px+component];
                    const char* names[]{"direct.pfm","indirect.pfm","total.pfm"};
                    pfm(gpu/names[component],image.width,image.height,values);
                }''',
             '''                deferred.retain(gpu,image.width,image.height,std::move(image.image_rgba));'''),
            ('            if(!timings)throw std::runtime_error("calibration timings write failed");',
             '''            deferred.flush(out,[&](const auto& image) {
                for(uint32_t component=0;component<3;++component) {
                    std::vector<float> values(size_t(image.width)*image.height);
                    for(size_t px=0;px<values.size();++px)values[px]=image.rgba[4*px+component];
                    const char* names[]{"direct.pfm","indirect.pfm","total.pfm"};
                    pfm(image.directory/names[component],image.width,image.height,values);
                }
            });
            if(!timings)throw std::runtime_error("calibration timings write failed");''')],
        'pt':[
            ('int main(int argc,char** argv) {', SPOOL+'\nint main(int argc,char** argv) {'),
            ('        for(uint32_t f=0;f<frames;++f) {',
             '        N010DeferredImages deferred(doses.empty()?0:frames);\n        for(uint32_t f=0;f<frames;++f) {'),
            ('''            for(size_t c=0;c<3;++c) {
                const char* name=std::array<const char*,3>{"direct.pfm","indirect.pfm","total.pfm"}[c];
                pfm(frame_out/name,width,height,values,c);
                if(f+1==frames) pfm(out/name,width,height,values,c);
            }''',
             '''            if(!doses.empty()) deferred.retain(frame_out,width,height,std::move(values),f+1==frames);
            else for(size_t c=0;c<3;++c) {
                const char* name=std::array<const char*,3>{"direct.pfm","indirect.pfm","total.pfm"}[c];
                pfm(frame_out/name,width,height,values,c);
                if(f+1==frames) pfm(out/name,width,height,values,c);
            }'''),
            ('        times<<"]}\\n"; if(!times) throw std::runtime_error("timing output failed");',
             '''        if(!doses.empty()) deferred.flush(out,[&](const auto& image) {
            for(size_t c=0;c<3;++c) {
                const char* name=std::array<const char*,3>{"direct.pfm","indirect.pfm","total.pfm"}[c];
                pfm(image.directory/name,image.width,image.height,image.rgba,c);
                if(image.root) pfm(out/name,image.width,image.height,image.rgba,c);
            }
        });
        times<<"]}\\n"; if(!times) throw std::runtime_error("timing output failed");''')],
    }


def validate_parent(generated,inputs):
    from qualify_hybrid_references import check_files
    path = RESULTS/'167-bulk-pfm-calibration-fixture-build.json'
    if B.sha(path)!='71b94470b465f0d16afaec9bec60b42e63c39e6be8ed781f6d5b1802ca99b88a':
        raise ValueError('immutable parent build changed')
    proof = json.loads(path.read_bytes()); inputs[str(path)] = B.sha(path)
    if not proof['complete'] or not proof['all_pass'] or not proof['active_inputs_byte_unchanged']:
        raise ValueError('parent build proof incomplete')
    check_files(proof['input_sha256'],inputs)
    parent = ROOT/'out/research/n010-comparison-readiness/minimal-calibration-build-v3'
    check_files({str(parent/n):h for n,h in proof['generated_sha256'].items()},inputs)
    restored = {}
    for key in ('runtime','capture','pt'):
        source = generated[key]
        for old,new in reversed(pairs().get(key,[])):
            source = B.once(source,new,old)
        if source!=(parent/('minimal_'+key+'.cpp')).read_text():
            raise ValueError('whole deferred-source inverse differs from parent 167')
        restored[key] = source
    B.validate_v2(restored,inputs)
    # Explicitly compare the PT GPU lambda and complete timed maintenance prefix.
    old, new = restored['pt'], generated['pt']
    for start,stop in [('        const auto run_image=', '        for(uint32_t f='),
                       ('            const auto start=Clock::now();',
                        '            n::AllocationLedger::instance().phase("diagnostic-readback-')]:
        before = old[old.index(start):old.index(stop,old.index(start))]
        after = new[new.index(start):new.index(stop,new.index(start))]
        # Only CPU spool declaration was added after the run-image lambda.
        if start.endswith('run_image='):
            after = after.replace('        N010DeferredImages deferred(doses.empty()?0:frames);\n','')
        if before!=after:
            raise ValueError('timed PT source body changed')


def require_no_gpu():
    allowed_entries = {'recover_primary_direction_physical.py','validate_recovered_primary_direction_prefix.py',
        'acquire_recovered_primary_direction_feasibility.py','acquire_post_stop_primary_direction_feasibility.py',
        'acquire_after_second_stop_primary_direction_feasibility.py','qualify_recovered_primary_direction_references.py'}
    allowed_native = {str(ROOT/'out/research/n010-comparison-readiness/primary-direction-build-v1'/folder/name)
        for folder,name in [('standalone','n010_primary_direction_oracle'),('prefix','n010_primary_direction_prefix')]}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name)==os.getpid(): continue
        try:
            name=(p/'comm').read_text().strip()
            words=[w.decode(errors='replace') for w in (p/'cmdline').read_bytes().split(b'\0') if w]
        except OSError: continue
        allowed = bool(words) and (words[0] in allowed_native or any(Path(w).name in allowed_entries for w in words))
        research = any(w.startswith(('scripts/research/',str(ROOT/'scripts/research')+'/')) for w in words)
        if name.startswith(('phos-','gi_')) or ((name.startswith(('n010_','n008_oracle')) or research) and not allowed):
            raise ValueError('another GPU/research worker remains: '+p.name+' '+name)


def require_paths(work,output):
    if work.resolve()!=FIXTURE or output.resolve()!=OUTPUT:
        raise ValueError('registered fresh deferred fixture paths required')


def build_program():
    if B.sha(Path(B.__file__))!='4dd8209f331f7662e34a1fd1798ead90c47d1458c2c5efbd256f27500397fd0c':
        raise ValueError('frozen parent builder helper changed')
    source,scope = B.build_program()
    source = B.once(source,'Plan 048: isolated row-bulk PFM calibration fixture; no GPU dispatch.',
                    'Plan 054: isolated deferred-image calibration fixture; no GPU dispatch.')
    source = B.once(source,B.PLAN.name,PLAN.name)
    source = B.once(source,'n010-minimal-calibration-fixture-build/3','n010-minimal-calibration-fixture-build/4')
    source = B.once(source,'Path(_bulk_helper),','Path(_bulk_helper),Path(_deferred_helper),')
    source = B.once(source,"        result['active_inputs_byte_unchanged'] = True",
        "        result['whole_inverse_to_167'] = True\n"
        "        result['runtime_file_and_pt_timed_bodies_unchanged'] = True\n"
        "        result['cpu_rgba_capacity_bound_bytes'] = 256*1024**2\n"
        "        result['active_inputs_byte_unchanged'] = True")
    def combined():
        return {key:B.pairs()[key]+pairs()[key] for key in ('capture','pt')}
    scope.update(_bulk_pairs=combined,_validate_v2=validate_parent,
        _require_build_paths=require_paths,_require_no_gpu=require_no_gpu,
        _deferred_helper=str(Path(__file__).resolve()))
    return source,scope
