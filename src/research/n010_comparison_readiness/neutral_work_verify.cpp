// Exact CPU witness for calibration's independent, non-image uint32 work.
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
int main(int argc,char** argv) {
    try {
        if(argc!=3)throw std::runtime_error("usage: verifier DOSE FILE");
        const auto dose=std::stoul(argv[1]);if(dose>100000000)throw std::runtime_error("dose ceiling");
        std::ifstream in(argv[2],std::ios::binary);std::array<uint32_t,16384> values{};
        in.read(reinterpret_cast<char*>(values.data()),sizeof(values));
        if(!in||in.peek()!=std::char_traits<char>::eof())throw std::runtime_error("scratch shape");
        for(uint32_t index:{0U,1U,64U,127U,8191U,16383U}) {
            uint32_t expected=index^0x4e303130U;
            for(uint32_t j=0;j<dose;++j) {expected=expected*1664525U+1013904223U;expected^=expected>>13U;}
            if(values[index]!=expected)throw std::runtime_error("known-work witness mismatch");
        }
        std::cout<<"PASS\n";
    } catch(const std::exception& e) {std::cerr<<e.what()<<"\n";return 1;}
}
