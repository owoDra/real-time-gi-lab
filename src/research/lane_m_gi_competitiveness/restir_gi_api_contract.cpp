// 033 actual pinned host SDK execution; independent addressing/routing assertions.
#include <Rtxdi/GI/ReSTIRGI.h>
#include <array>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
namespace fs=std::filesystem;
unsigned checks=0;
void require(bool ok) {++checks;if(!ok)throw std::runtime_error("033 host SDK contract failed");}
template<class T> void save(const fs::path& path,const std::vector<T>& v) {
 require(!fs::exists(path));std::ofstream f(path,std::ios::binary);require(bool(f));
 f.write(reinterpret_cast<const char*>(v.data()),std::streamsize(v.size()*sizeof(T)));require(bool(f));
}
int main(int argc,char** argv) {
 try {
 require(argc==3&&std::string(argv[1])=="--out");fs::path out=argv[2];require(!fs::exists(out));require(fs::create_directory(out));
 require(sizeof(RTXDI_PackedGIReservoir)==32);
 require(offsetof(RTXDI_PackedGIReservoir,position)==0&&offsetof(RTXDI_PackedGIReservoir,packed_miscData_age_M)==12);
 require(offsetof(RTXDI_PackedGIReservoir,packed_radiance)==16&&offsetof(RTXDI_PackedGIReservoir,weight)==20);
 require(offsetof(RTXDI_PackedGIReservoir,packed_normal)==24&&offsetof(RTXDI_PackedGIReservoir,unused)==28);
 require(rtxdi::c_NumReSTIRGIReservoirBuffers==2&&RTXDI_RESERVOIR_BLOCK_SIZE==16);
 std::cout<<"{\"complete\":true,\"gpu_executed\":false,\"packed_stride\":32,\"states\":[";
 unsigned states=0,addressMaps=0;std::uint64_t addressCount=0;
 for(auto size:std::array<std::array<unsigned,2>,3>{{{1,1},{320,180},{321,181}}}) for(unsigned checker=0;checker<3;++checker) {
  const auto w=size[0],h=size[1],rw=checker?(w+1)/2:w;
  const auto row=((rw+15)/16)*256,array=row*((h+15)/16);
  rtxdi::ReSTIRGIStaticParameters sp;sp.RenderWidth=w;sp.RenderHeight=h;sp.CheckerboardSamplingMode=rtxdi::CheckerboardMode(checker);
  rtxdi::ReSTIRGIContext context(sp);auto buffers=context.GetReservoirBufferParameters();
  require(buffers.reservoirBlockRowPitch==row&&buffers.reservoirArrayPitch==array);
  auto defaults=context.GetSpatialResamplingParameters();auto temporal=context.GetTemporalResamplingParameters();
  require(defaults.numSamples==2&&defaults.samplingRadius==32.f&&defaults.depthThreshold==.1f&&defaults.normalThreshold==.6f);
  require(defaults.biasCorrectionMode==RTXDI_GIBiasCorrectionMode::Basic);
  require(temporal.maxHistoryLength==8&&temporal.maxReservoirAge==30&&temporal.enableFallbackSampling==1&&temporal.enablePermutationSampling==0);
  require(context.GetBoilingFilterParameters().enableBoilingFilter==1&&context.GetBoilingFilterParameters().boilingFilterStrength==.2f);
  require(context.GetFinalShadingParameters().enableFinalVisibility==1&&context.GetFinalShadingParameters().enableFinalMIS==1);
  std::vector<unsigned> addresses;std::vector<bool> seen(2*array,false);
  for(unsigned a=0;a<2;++a)for(unsigned y=0;y<h;++y)for(unsigned x=0;x<rw;++x) {
   // Formula independent of SDK host pitch construction; shader addressing is audited separately.
   auto pointer=a*array+(y/16)*row+(x/16)*256+(y%16)*16+x%16;
   require(pointer<(a+1)*array&&pointer>=a*array&&!seen[pointer]);seen[pointer]=true;addresses.push_back(pointer);
  }
  save(out/("addresses-"+std::to_string(w)+"x"+std::to_string(h)+"-"+std::to_string(checker)+".u32"),addresses);
  ++addressMaps;addressCount+=addresses.size();
  for(unsigned mode=0;mode<5;++mode) {
   context.SetResamplingMode(rtxdi::ReSTIRGI_ResamplingMode(mode));
   for(unsigned frame=0;frame<64;++frame) {
    context.SetFrameIndex(frame);const auto b=context.GetBufferIndices();auto t=context.GetTemporalResamplingParameters();
    require(context.GetFrameIndex()==frame&&context.GetResamplingMode()==rtxdi::ReSTIRGI_ResamplingMode(mode));
    require(t.uniformRandomNumber==rtxdi::JenkinsHash(frame));
    const auto initial=b.secondarySurfaceReSTIRDIOutputBufferIndex,final=b.finalShadingInputBufferIndex;
    require(initial<2&&final<2);
    if(mode==0)require(initial==0&&final==0);
    if(mode==1)require(initial==(frame&1)&&b.temporalResamplingInputBufferIndex==1-initial&&b.temporalResamplingOutputBufferIndex==initial&&final==initial);
    if(mode==2)require(initial==0&&b.spatialResamplingInputBufferIndex==0&&b.spatialResamplingOutputBufferIndex==1&&final==1);
    if(mode==3)require(initial==0&&b.temporalResamplingInputBufferIndex==1&&b.temporalResamplingOutputBufferIndex==0&&b.spatialResamplingInputBufferIndex==0&&b.spatialResamplingOutputBufferIndex==1&&final==1);
    if(mode==4)require(initial==(frame&1)&&b.temporalResamplingInputBufferIndex==1-initial&&b.spatialResamplingOutputBufferIndex==initial&&final==initial);
    if(states++)std::cout<<',';
    std::cout<<'['<<w<<','<<h<<','<<checker<<','<<mode<<','<<frame<<','<<row<<','<<array<<','<<initial<<','<<b.temporalResamplingInputBufferIndex<<','<<b.temporalResamplingOutputBufferIndex<<','<<b.spatialResamplingInputBufferIndex<<','<<b.spatialResamplingOutputBufferIndex<<','<<final<<','<<2ULL*array*32<<']';
   }
  }
  // Setter contracts are explicit: selected fixture values, not quality tuning.
  defaults.numSamples=4;defaults.biasCorrectionMode=RTXDI_GIBiasCorrectionMode::Raytraced;context.SetSpatialResamplingParameters(defaults);
  require(context.GetSpatialResamplingParameters().numSamples==4&&context.GetSpatialResamplingParameters().biasCorrectionMode==RTXDI_GIBiasCorrectionMode::Raytraced);
  temporal.maxHistoryLength=4;temporal.maxReservoirAge=12;context.SetTemporalResamplingParameters(temporal);
  require(context.GetTemporalResamplingParameters().maxHistoryLength==4&&context.GetTemporalResamplingParameters().maxReservoirAge==12);
  auto fused=context.GetSpatioTemporalResamplingParameters();fused.numSamples=4;fused.biasCorrectionMode=RTXDI_GIBiasCorrectionMode::Raytraced;context.SetSpatioTemporalResamplingParameters(fused);
  require(context.GetSpatioTemporalResamplingParameters().numSamples==4&&context.GetSpatioTemporalResamplingParameters().biasCorrectionMode==RTXDI_GIBiasCorrectionMode::Raytraced);
  auto boiling=context.GetBoilingFilterParameters();boiling.enableBoilingFilter=0;context.SetBoilingFilterParameters(boiling);require(context.GetBoilingFilterParameters().enableBoilingFilter==0);
  auto shading=context.GetFinalShadingParameters();shading.enableFinalMIS=0;context.SetFinalShadingParameters(shading);require(context.GetFinalShadingParameters().enableFinalMIS==0);
 }
 std::vector<std::uint8_t> offsets(8192*2);rtxdi::FillNeighborOffsetBuffer(offsets.data(),8192);save(out/"neighbor-offsets.u8",offsets);
 for(unsigned i=0;i<8192;++i){int x=std::int8_t(offsets[i*2]),y=std::int8_t(offsets[i*2+1]);require(x*x+y*y<=125*125);}
 require(states==2880&&addressMaps==9);
 std::cout<<"],\"state_count\":"<<states<<",\"address_maps\":"<<addressMaps<<",\"address_count\":"<<addressCount<<",\"neighbor_offsets\":8192,\"assertions\":"<<checks<<",\"all_pass\":true}\n";
 return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
