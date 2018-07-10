#include <SDL2/SDL.h>

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

struct kwz_header
{
	uint32_t crc;
	unsigned int creation_time;
	unsigned int edit_time;
	uint32_t version;
	char original_id[10];
	char parent_id[10];
	char child_id[10];
	uint16_t original_username[11];
	uint16_t parent_username[11];
	uint16_t current_username[11];
	char original_filename[28];
	char parent_filename[28];
	char current_filename[28];
	uint16_t frame_count;
	uint16_t thumbnail_frame;
	uint16_t flags;
	uint8_t speed;
	uint8_t layer_flags;
};

struct kwz_frame_info
{
	uint32_t flags;
	uint16_t layer_a_size;
	uint16_t layer_b_size;
	uint16_t layer_c_size;
	char author_id[10];
	uint8_t layer_a_depth;
	uint8_t layer_b_depth;
	uint8_t layer_c_depth;
	uint8_t sound_flags;
	uint32_t camera_flags;
};

struct kwz
{
	struct kwz_header header;
	const char *thumbnail_data;
	size_t thumbnail_size;
	struct kwz_frame_info *frame_infos;
	char *flip_data;
	size_t flip_data_size;

	int current_frame;
	off_t current_frame_offset;
	int frame_delay;
};

uint8_t comptable1[256];
uint32_t comptable2[6561];

uint32_t comptable3[] = {
    0x00000000, 0x11111111, 0xFFFFFFFF, 0x00000001, 
    0x00000010, 0x00000100, 0x00001000, 0x00010000, 
    0x00100000, 0x01000000, 0x10000000, 0x0000000F, 
    0x000000F0, 0x00000F00, 0x0000F000, 0x000F0000, 
    0x00F00000, 0x0F000000, 0xF0000000, 0x00000011, 
    0x00000110, 0x00001100, 0x00011000, 0x00110000,
    0x01100000, 0x11000000, 0x01010101, 0x10101010, 
    0x0F0F0F0F, 0xF0F0F0F0, 0x1F1F1F1F, 0xF1F1F1F1
};

uint16_t comptable4[] = {
	0x0000, 0x0CD0, 0x19A0, 0x02D9, 0x088B, 0x0051, 0x00F3, 0x0009,
    0x001B, 0x0001, 0x0003, 0x05B2, 0x1116, 0x00A2, 0x01E6, 0x0012,
    0x0036, 0x0002, 0x0006, 0x0B64, 0x08DC, 0x0144, 0x00FC, 0x0024,
    0x001C, 0x0004, 0x0334, 0x099C, 0x0668, 0x1338, 0x1004, 0x166C
};

uint64_t linedefs[52488/8];

void read_file(const char *filename, void *ptr, size_t size)
{
	FILE *table = fopen(filename, "rb");
	if(table == NULL)
	{
		fprintf(stderr, "Failed to open %s!\n", filename);
		exit(0);
	}
	int read_count = fread(ptr, 1, size, table);
	if(read_count != size)
	{
		fprintf(stderr, "%s is too small!\n", filename);
		exit(0);
	}
	fclose(table);
}

void read_kwz(struct kwz *kwz, FILE *kwz_file)
{
	kwz->current_frame = 0;
	kwz->current_frame_offset = 0;

	fseek(kwz_file, 0, SEEK_END);
	size_t file_size = ftell(kwz_file) - 256; // Size, except the RSA signature at the end.
	fseek(kwz_file, 0, SEEK_SET);

	off_t offset = 0;

	while(offset < file_size)
	{
		char magic[4];
		uint32_t size;
		fread(magic, 4, 1, kwz_file);
		magic[3] = 0;
		fread(&size, 4, 1, kwz_file);

		//printf("Got section %s, length %i\n", magic, size);
		if(memcmp(magic, "KFH", 3) == 0)
		{
			if(size != sizeof(struct kwz_header))
			{
				printf("Something is broken! Badly!\n");
				exit(1);
			}
			fread(&kwz->header, sizeof(struct kwz_header), 1, kwz_file);

			//printf("Got KWZ with %i frames!\n", kwz->header.frame_count);
			kwz->frame_infos = malloc(sizeof(struct kwz_frame_info) * kwz->header.frame_count);

			uint32_t speed_table[] = {
				5000,
				2000,
				1000,
				500,
				250,
				166, // 1/6 of a sec
				125,
				83, // 1/12th
				50,
				41, // 1/24th
				33 // 1/30th
			};

			kwz->frame_delay = speed_table[kwz->header.speed];
		}
		else if(memcmp(magic, "KTN", 3) == 0)
		{
			uint32_t unk;
			fread(&unk, 4, 1, kwz_file);
			size_t jpeg_size = size - 4;
			//printf("jpeg size %i\n", jpeg_size);
			char *jpeg_data = malloc(jpeg_size);
			fread(jpeg_data, 1, jpeg_size, kwz_file);
		}
		else if(memcmp(magic, "KMI", 3) == 0)
		{
			if(sizeof(struct kwz_frame_info) != 28)
			{
				printf("Something is broken! Badly!\n");
				exit(1);
			}

			fread(kwz->frame_infos, sizeof(struct kwz_frame_info), kwz->header.frame_count, kwz_file);
		}
		else if(memcmp(magic, "KMC", 3) == 0)
		{
			uint32_t unk;
			fread(&unk, 4, 1, kwz_file);

			size_t flip_data_size = size - 4;
			kwz->flip_data = malloc(flip_data_size);
			fread(kwz->flip_data, 1, flip_data_size, kwz_file);
		}
		offset += size + 8;
		fseek(kwz_file, offset, SEEK_SET);
	}
}

struct bitstream
{
	uint8_t *data;
	uint32_t curr;
	int curr_int;
	int curr_bit;
};

uint16_t read_bits(struct bitstream *b, int n_bits)
{
	if(b->curr_bit + n_bits > 16)
	{
		uint32_t next_bits = (uint32_t)((uint16_t*)b->data)[b->curr_int++];
		b->curr |= next_bits << (16- b->curr_bit);
		b->curr_bit -= 16;
	}
	
	uint16_t mask = (1 << n_bits) - 1;
    uint16_t result = b->curr & mask;

	b->curr >>= n_bits;
	b->curr_bit += n_bits;
	return result;
}

#define ROR(value, bits) (((value >> bits) | (value << (32 - bits))) & 0xFFFFFFFF)

void deswizzle_layer(char *layer_data, uint8_t *result_buffer)
{
	/*layer_offset = 0
      tileIndex = 0

      # loop through 128 * 128 large tiles
      for tileOffsetY in range(0, 240, 128):
        for tileOffsetX in range(0, 320, 128):
          # each large tile is made of 8 * 8 small tiles
          for subTileOffsetY in range(0, 128, 8):
            y = tileOffsetY + subTileOffsetY
            # if the tile falls off the bottom of the frame, jump to the next large tile
            if y >= 240: break

            for subTileOffsetX in range(0, 128, 8):
              x = tileOffsetX + subTileOffsetX
              # if the tile falls off the right of the frame, jump to the next small tile row
              if x >= 320: break
              
              # unpack the 8*8 tile - (x, y) gives the position of the tile's top-left pixel
              for lineIndex in range(0, 8):
                # get the line data
                # each line is defined as an uint16 offset into a table of all possible line values
                lineValue = layer_buffer[layer_offset]
                # in certain cases we have to flip the endianess because... of course?
                if lineValue > 0x3340:
                  lineValue = ((lineValue) >> 8) | ((lineValue & 0x00FF) << 8)

                lineValue *= 8
                result_buffer[y + lineIndex][x : x + 8] = self.linedefs[lineValue:lineValue + 8]
                layer_offset += 1*/
	struct bitstream b;
	b.data = layer_data;
	b.curr = 0;
	b.curr_int = 0;
	b.curr_bit = 16;

	int x,y;
	int skip = 0;
	uint8_t tile_buffer[64];

	for(int tileOffsetY = 0; tileOffsetY < 240; tileOffsetY += 128)
	{
		for(int tileOffsetX = 0; tileOffsetX < 320; tileOffsetX += 128)
		{
			for(int subTileOffsetY = 0; subTileOffsetY < 128; subTileOffsetY += 8)
			{
				y = subTileOffsetY + tileOffsetY;
				if(y >= 240) break;

				for(int subTileOffsetX = 0; subTileOffsetX < 128; subTileOffsetX += 8)
				{
					x = subTileOffsetX + tileOffsetX;
					if(x >= 320) break;
					
					if(skip-- > 0) continue;

					uint8_t block_type = read_bits(&b, 3);
					switch(block_type)
					{
						case 0:
						{
							uint16_t a = comptable4[read_bits(&b, 5)];
							for(int i = 0; i < 8; i++)
							{
								memcpy(&tile_buffer[i*8], &linedefs[a], 8);
							}
						}
						break;

						case 1:
						{
							uint16_t value = read_bits(&b, 13);
							for(int i = 0; i < 8; i++)
							{
								memcpy(&tile_buffer[i*8], &linedefs[value], 8);
							}
						}
						break;

						case 2:
						{
							uint8_t index1 = read_bits(&b, 5);
							uint32_t index2 = ROR(comptable3[index1], 4);
							uint16_t v1 = comptable1[index2 & 0xFF];
							uint16_t v2 = comptable1[(index2 >> 8) & 0xFF];
							uint16_t v3 = comptable1[(index2 >> 16) & 0xFF];
							uint16_t v4 = comptable1[index2 >> 24];
							uint16_t x_value = comptable4[index1];
							uint16_t y_value = ((v1 * 9 + v2) * 9 + v3) * 9 + v4;

							for(int i = 0; i < 8; i++)
							{
								if(i%2)
									memcpy(&tile_buffer[i*8], &linedefs[y_value], 8);
								else
									memcpy(&tile_buffer[i*8], &linedefs[x_value], 8);
							}
						}
						break;

						case 3:
						{
							uint16_t x_value = read_bits(&b, 13);
							uint32_t index = ROR(comptable2[x], 4);
							uint16_t v1 = comptable1[index & 0xFF];
							uint16_t v2 = comptable1[(index >> 8) & 0xFF];
							uint16_t v3 = comptable1[(index >> 16) & 0xFF];
							uint16_t v4 = comptable1[index >> 24];
							uint16_t y_value = ((v1 * 9 + v2) * 9 + v3) * 9 + v4;

							for(int i = 0; i < 8; i++)
							{
								if(i%2)
									memcpy(&tile_buffer[i*8], &linedefs[y_value], 8);
								else
									memcpy(&tile_buffer[i*8], &linedefs[x_value], 8);
							}
						}
						break;

						case 4:
						{
							uint8_t mask = read_bits(&b, 8);
							for(int i = 0; i < 8; i++)
							{
								uint16_t line_value;
								if(mask & (1<<i))
								{
									line_value = comptable4[read_bits(&b, 5)];
								}
								else
								{
									line_value = read_bits(&b, 13);
								}
								memcpy(&tile_buffer[i*8], &linedefs[line_value], 8);
							}
						}
						break;

						case 5:
							skip = read_bits(&b, 5);
							continue;
						break;

						case 7:
						{
					        uint8_t pattern = read_bits(&b, 2);
					        uint8_t use_table = read_bits(&b, 1);
					        uint16_t x_value, y_value;
					        uint8_t x,y;
					        if(use_table)
					        {
					          x_value = comptable4[read_bits(&b, 5)];
					          y_value = comptable4[read_bits(&b, 5)];
					          pattern = (pattern + 1) % 4;
					        }
					        else
					        {
					          x_value = read_bits(&b, 13);
					          y_value = read_bits(&b, 13);
					        }
					        /*if pattern == 0: layer_buffer[layer_offset:layer_offset + 8] = [x, y, x, y, x, y, x, y]
					        elif pattern == 1: layer_buffer[layer_offset:layer_offset + 8] = [x, x, y, x, x, y, x, x]
					        elif pattern == 2: layer_buffer[layer_offset:layer_offset + 8] = [x, y, x, x, y, x, x, y]
					        elif pattern == 3: layer_buffer[layer_offset:layer_offset + 8] = [x, y, y, x, y, y, x, y]*/

					        // i am 100% out of fucks
					        // 8:16am

					        switch(pattern)
					        {
					        	case 0:
					        		memcpy(&tile_buffer[0], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[8], &linedefs[y_value], 8);
					        		memcpy(&tile_buffer[16], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[24], &linedefs[y_value], 8);
					        		memcpy(&tile_buffer[32], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[40], &linedefs[y_value], 8);
					        		memcpy(&tile_buffer[48], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[56], &linedefs[y_value], 8);
					        	break;
					        	case 1:
					        		memcpy(&tile_buffer[0], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[8], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[16], &linedefs[y_value], 8);
					        		memcpy(&tile_buffer[24], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[32], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[40], &linedefs[y_value], 8);
					        		memcpy(&tile_buffer[48], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[56], &linedefs[x_value], 8);
					        	break;
					        	case 2:
					        		memcpy(&tile_buffer[0], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[8], &linedefs[y_value], 8);
					        		memcpy(&tile_buffer[16], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[24], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[32], &linedefs[y_value], 8);
					        		memcpy(&tile_buffer[40], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[48], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[56], &linedefs[y_value], 8);
					        	break;
					        	case 3:
					        		memcpy(&tile_buffer[0], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[8], &linedefs[y_value], 8);
					        		memcpy(&tile_buffer[16], &linedefs[y_value], 8);
					        		memcpy(&tile_buffer[24], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[32], &linedefs[y_value], 8);
					        		memcpy(&tile_buffer[40], &linedefs[y_value], 8);
					        		memcpy(&tile_buffer[48], &linedefs[x_value], 8);
					        		memcpy(&tile_buffer[56], &linedefs[y_value], 8);
					        	break;
					        }
			        	}
			        	break;
						default:
							printf("Unhandled tile type %i!\n", block_type);
							exit(1);
						break;
					}

					for(int line = 0; line < 8; line++)
					{
						memcpy(&result_buffer[(y+line)*320 + x], &tile_buffer[line*8], 8);
					}
				}
			}
		}
	}
}

// TODO: precalc frame/layer offsets so we can decode any arbitrary frame.
void decode_frame(struct kwz *kwz, uint8_t *layer_a, uint8_t *layer_b, uint8_t *layer_c)
{
	struct kwz_frame_info *f_info = &kwz->frame_infos[kwz->current_frame];
	uint16_t layer_buffer[9600];
	char *ptr = kwz->flip_data + kwz->current_frame_offset;

	deswizzle_layer(ptr, layer_a);
	ptr += f_info->layer_a_size;
	kwz->current_frame_offset += f_info->layer_a_size;

	deswizzle_layer(ptr, layer_b);
	ptr += f_info->layer_b_size;
	kwz->current_frame_offset += f_info->layer_b_size;

	deswizzle_layer(ptr, layer_c);
	ptr += f_info->layer_c_size;
	kwz->current_frame_offset += f_info->layer_c_size;
}

#define RGBA8(r,g,b) (r << 24) | (g << 16) | (b << 8) | 0xff

uint32_t palette[] = {
    RGBA8(0xff, 0xff, 0xff),
    RGBA8(0x14, 0x14, 0x14),
    RGBA8(0xff, 0x45, 0x45),
    RGBA8(0xff, 0xe6, 0x00),
    RGBA8(0x00, 0x82, 0x32),
    RGBA8(0x06, 0xAE, 0xff),
    RGBA8(0xff, 0xff, 0xff),
};

void get_frame_palette(struct kwz_frame_info *frame, uint32_t *frame_palette)
{
	uint32_t flags = frame->flags;
	frame_palette[0] = palette[flags & 0xF]; // paper color
	frame_palette[1] = palette[(flags >> 8) & 0xF];  // layer A color 1
	frame_palette[2] = palette[(flags >> 12) & 0xF]; // layer A color 2
	frame_palette[3] = palette[(flags >> 16) & 0xF]; // layer B color 1
	frame_palette[4] = palette[(flags >> 20) & 0xF]; // layer B color 2
	frame_palette[5] = palette[(flags >> 24) & 0xF]; // layer C color 1
	frame_palette[6] = palette[(flags >> 28) & 0xF]; // layer C color 2
}

int main(int argc, char **argv)
{
	if(argc < 2)
	{
		fprintf(stderr, "Usage: %s [kwz]\n", argv[0]);
		return 1;
	}
	
	memset(comptable1, 8, 256);
	comptable1[0] = 0x00;
    comptable1[1] = 0x01;
    comptable1[15] = 0x02;
    comptable1[16] = 0x03;
    comptable1[17] = 0x04;
    comptable1[31] = 0x05;
    comptable1[240] = 0x06;
    comptable1[241] = 0x07;

	uint8_t wat_values[] = {0, 1, 0xF, 0x10, 0x11, 0x1F, 0xF0, 0xF1, 0xFF};
	int i = 0;
	memset(comptable2, 0, sizeof(comptable2));

    for(int a = 0; a < 9; a++)
      for(int b = 0; b < 9; b++)
        for(int c = 0; c < 9; c++)
          for(int d = 0; d < 9; d++)
          {
            uint32_t value = (wat_values[a] << 24) | (wat_values[b] << 16) | (wat_values[c] << 8) | wat_values[d];
            comptable2[i++] = value;
          }

	read_file("../linetable.bin", linedefs, sizeof(linedefs));

	struct kwz kwz;
	FILE *kwz_file = fopen(argv[1], "rb");
	read_kwz(&kwz, kwz_file);

	uint8_t *layer_a_fb = malloc(320*240);
	uint8_t *layer_b_fb = malloc(320*240);
	uint8_t *layer_c_fb = malloc(320*240);

	uint32_t *layer_fb = malloc(320*240*4);
	memset(layer_fb, 0, 320*240*4);

	uint32_t frame_palette[8];

	SDL_Window *w = SDL_CreateWindow("blah", 100, 100, 320, 240, 0);
	SDL_Surface *tex_surf = SDL_CreateRGBSurfaceWithFormatFrom(layer_fb, 320, 240, 32, 320 * 4, SDL_PIXELFORMAT_RGBA8888);
	if(tex_surf == NULL)
	{
		printf("wot %s\n", SDL_GetError());
		return 1;
	}

	SDL_Surface *window_surf = SDL_GetWindowSurface(w);
	SDL_Event e;
	while(1)
	{
		while(SDL_PollEvent(&e))
		{
			if(e.type == SDL_QUIT)
			{
				SDL_DestroyWindow(w);
				return 0;
			}
		}

		struct kwz_frame_info *f_info = &kwz.frame_infos[kwz.current_frame];
		get_frame_palette(f_info, frame_palette);
		decode_frame(&kwz, layer_a_fb, layer_b_fb, layer_c_fb);
		kwz.current_frame++;

		for(int y = 0; y < 240; y++)
		{
			for(int x = 0; x < 320; x++)
			{
				uint8_t a = layer_a_fb[y*320+x];
				uint8_t b = layer_b_fb[y*320+x];
				uint8_t c = layer_c_fb[y*320+x];
				if(c)
				{
					layer_fb[y*320+x] = frame_palette[c + 4];
				}
				else if(b)
				{
					layer_fb[y*320+x] = frame_palette[b + 2];
				}
				else if(a)
				{
					layer_fb[y*320+x] = frame_palette[a];
				}
				else
				{
					layer_fb[y*320+x] = frame_palette[0];
				}
			}	
		}

		SDL_BlitSurface(tex_surf, NULL, window_surf, NULL);
		SDL_UpdateWindowSurface(w);
		SDL_Delay(kwz.frame_delay);
		if(kwz.current_frame >= kwz.header.frame_count) break;
	}
	SDL_DestroyWindow(w);

	return 0;
}