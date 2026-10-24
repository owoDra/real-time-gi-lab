#version 450
#extension GL_GOOGLE_include_directive : require
layout(local_size_x=32) in;
layout(set=0,binding=0,std430) readonly buffer Hits {uint hits[];};
layout(set=0,binding=1,std430) readonly buffer Camera {float camera[];};
layout(set=0,binding=2,std430) buffer Geometry {float geometry[];};
layout(set=0,binding=3,std430) buffer Coefficients {float coefficients[];};
layout(set=0,binding=4,std430) buffer Maps {uint maps[];};
layout(set=0,binding=5,std430) readonly buffer Sources {float sources[];};
layout(set=0,binding=6,std430) buffer Stages {float stages[];};
layout(set=0,binding=7,std430) buffer Raw {float unclipped[];};
layout(push_constant) uniform Push {uint mode;uint stage;uint start;uint count;} push;
#define Q_OUT out
uint q_width(){return uint(camera[18]);}uint q_height(){return uint(camera[19]);}
uint q_size(){return q_width()*q_height();}uint q_images(){return uint(camera[17]);}
uint q_hit(uint p,uint w){return hits[p*8+w];}float q_camera(uint a){return camera[a];}
float q_fbits(uint x){return uintBitsToFloat(x);}float q_sqrt(float x){return sqrt(x);}
float q_abs(float x){return abs(x);}float q_floor(float x){return floor(x);}
float q_max(float x,float y){return max(x,y);}int q_iabs(int x){return abs(x);}int q_imax(int x,int y){return max(x,y);}
float q_getgeo(uint p,uint a){return geometry[p*8+a];}void q_setgeo(uint p,uint a,float v){geometry[p*8+a]=v;}
float q_getcoeff(uint s,uint j,uint p){return coefficients[(s*25+j)*q_size()+p];}
void q_setcoeff(uint s,uint j,uint p,float v){coefficients[(s*25+j)*q_size()+p]=v;}
void q_setmask(uint s,uint p,uint v){maps[s*q_size()+p]=v;}
void q_setselector(uint s,uint p,uint v){maps[(3+s)*q_size()+p]=v;}
float q_source(uint i,uint p){return sources[i*q_size()+p];}
float q_readstage(uint i,uint s,uint p){return stages[(i*3+s)*q_size()+p];}
void q_writestage(uint i,uint s,uint p,float r,float v){uint o=(i*3+s)*q_size()+p;unclipped[o]=r;stages[o]=v;}
#include "surface_quadratic_shared.glslinc"
void main(){uint offset=gl_GlobalInvocationID.x;if(offset>=push.count)return;uint pixel=push.start+offset;
    if(pixel>=q_size())return;uint stride=1u<<push.stage;
    if(push.mode==0)q_geometry(pixel);else if(push.mode==1)q_fit(pixel,stride,push.stage);else if(push.mode==2)q_apply(pixel,stride,push.stage);
}
