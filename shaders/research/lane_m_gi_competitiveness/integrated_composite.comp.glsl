#version 450
layout(local_size_x=32) in;
layout(binding=0,std430) readonly buffer RawImage {vec4 raw_pixels[];};
layout(binding=1,std430) readonly buffer Filtered {float stages[];};
layout(binding=2,std430) writeonly buffer FinalImage {vec4 final_pixels[];};
void main(){uint p=gl_GlobalInvocationID.x;if(p>=57600u)return;
    precise float direct=raw_pixels[p].x;precise float indirect=stages[115200u+p];
    precise float total=direct+indirect;final_pixels[p]=vec4(direct,indirect,total,1.0);
}
