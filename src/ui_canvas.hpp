#pragma once
#include <cstddef>
#include <cstdint>
#include <string_view>
namespace sc::ui {
struct Color { uint8_t r=0, g=0, b=0, a=255; };
// Pixels are packed 0xAABBGGRR (R,G,B,A bytes on little-endian targets).
class Canvas {
public:
 Canvas(int width,int height,int stride_pixels,uint32_t* pixels);
 ~Canvas();
 Canvas(const Canvas&)=delete;
 Canvas& operator=(const Canvas&)=delete;
 int width() const{return width_;} int height() const{return height_;}
 void clear(Color); void fill_rect(int x,int y,int w,int h,Color);
 void outline_rect(int x,int y,int w,int h,Color,int thickness=1);
 void rounded_rect(int x,int y,int w,int h,int radius,Color,bool filled=true,int thickness=1);
 void line(int x0,int y0,int x1,int y1,Color,int thickness=1);
 void circle(int cx,int cy,int radius,Color,bool filled=true,int thickness=1);
 // Font bytes remain caller-owned and must outlive use by this canvas.
 bool set_font(const uint8_t* ttf_bytes,size_t length); void clear_font();
 // y is top of line box. max_width < 0 is unbounded; optional ellipsis truncates.
 void text(int x,int y,std::string_view utf8,float size,Color,int max_width=-1,bool ellipsis=false);
 int measure_text(std::string_view utf8,float size) const;
private:
 int width_,height_,stride_; uint32_t* pixels_; struct FontState; FontState* font_;
};
}
