#import <stdio.h>

typedef          char   int8;
typedef   signed char   sint8;
typedef unsigned char   uint8;
typedef          short  int16;
typedef   signed short  sint16;
typedef unsigned short  uint16;
typedef          int    int32;
typedef   signed int    sint32;
typedef unsigned int    uint32;

#define _BYTE  uint8
#define _WORD  uint16
#define _DWORD uint32
#define _QWORD uint64

typedef int8 BYTE;
typedef int16 WORD;
typedef int32 DWORD;
typedef int32 LONG;

typedef int bool;

#define LOBYTE(x)   (*((_BYTE*)&(x)))   // low byte
#define LOWORD(x)   (*((_WORD*)&(x)))   // low word
#define LODWORD(x)  (*((_DWORD*)&(x)))  // low dword
#define HIBYTE(x)   (*((_BYTE*)&(x)+1))
#define HIWORD(x)   (*((_WORD*)&(x)+1))
#define HIDWORD(x)  (*((_DWORD*)&(x)+1))
#define BYTEn(x, n)   (*((_BYTE*)&(x)+n))
#define WORDn(x, n)   (*((_WORD*)&(x)+n))

#define BYTE1(x)   BYTEn(x,  1)

#define __ROL__(x, y) _rotl(x, y)
unsigned int __ROL4__(unsigned int value, int count) { return __ROL__((unsigned int)value, count); }
unsigned int __ROR4__(unsigned int value, int count) { return __ROL__((unsigned int)value, -count); }

unsigned char compressionTableWat[0x20090];

unsigned char aTable[0x1000];

// sign flag
int8 __SETS__(int x)
{
    return x < 0;
}

// overflow flag of subtraction (x-y)
int8 __OFSUB__(int x, int y)
{
    int y2 = y;
    int8 sx = __SETS__(x);
    return (sx ^ __SETS__(y2)) & (sx ^ __SETS__(x-y2));
}

unsigned int __fastcall sub_239F08(unsigned __int8 *a1, int a2)
{
  int v2; // r3
  unsigned int v3; // r2
  char v4; // r12
  unsigned __int8 v5; // r3
  unsigned int v6; // r1
  unsigned __int16 *v7; // r4
  char v8; // r5
  unsigned __int8 v9; // r1
  unsigned int v10; // r3

  v2 = *a1;
  v3 = *((unsigned __int16 *)a1 + 6);
  v4 = 16 - a2;
  if ( v2 >= 16 - a2 )
  {
	printf("if 1\n");
    v7 = (unsigned __int16 *)*((_DWORD *)a1 + 2);
	printf("v7: %x \n", v7);
    v8 = 16 - v2;
    v9 = v2 - v4;
    *((_DWORD *)a1 + 2) = v7 + 1;
	printf("v7: %x \n", *((_DWORD *)a1 + 2));
    v10 = *v7;
    *a1 = v9;
    v6 = v10 >> v9;
    v3 = (unsigned __int16)(v3 | ((_WORD)v10 << v8));
  }
  else
  {
	printf("if 2\n");  
    v5 = v2 + a2;
    v6 = v3 >> a2;
    *a1 = v5;
  }
  *((_WORD *)a1 + 6) = v6;
  printf("returning...\n");
  return (0xFFFFu >> v4) & v3;
}

unsigned int __fastcall sub_186B7C(int a1, unsigned short *a2, signed int a3)
{
  unsigned short *v3; // r5
  int v4; // r4
  signed int v5; // r9
  signed int v6; // r6
  int v7; // r1
  unsigned int result; // r0
  signed int v9; // r7
  bool v10; // zf
  bool v11; // nf
  unsigned __int8 v12; // vf
  unsigned int v13; // r1
  unsigned short *v14; // r2
  unsigned short *v15; // r0
  signed int v16; // r11
  int v17; // pc
  __int16 v18; // r6
  __int16 v19; // r6
  unsigned __int8 v20; // r0
  signed int v21; // r1
  __int16 v22; // r2
  unsigned int v23; // r0
  int v24; // r2
  bool v25; // zf
  bool v26; // nf
  unsigned __int8 v27; // vf
  unsigned int v28; // r2
  unsigned short *v29; // r3
  unsigned short *v30; // r0
  signed int v31; // r2
  int v32; // r1
  int v33; // r0
  __int16 v34; // r1
  unsigned int v35; // r0
  unsigned __int8 *v36; // r2
  unsigned __int8 *v37; // r12
  int v38; // r4
  int v39; // r6
  int v40; // r12
  int v41; // r2
  unsigned int v42; // r2
  unsigned __int8 *v43; // r3
  unsigned __int8 *v44; // r12
  int v45; // r4
  int v46; // r3
  int v47; // r12
  int v48; // r2
  int v49; // r1
  int v50; // r7
  unsigned int v51; // r6
  __int16 v52; // r6
  __int16 v53; // r6
  __int16 v54; // r6
  __int16 v55; // r6
  __int16 v56; // r6
  __int16 v57; // r6

  v3 = a2;
  v4 = a1;
  v5 = a3;
  printf("\n%x\n",(a3 / 0xFFFFFFFE));
  v6 = (signed int)&a2[a3 / 0xFFFFFFFE];
  printf("\n%x\n",(v6));
  v7 = *(unsigned int *)(a1 + 124);
  result = (unsigned int)v3;
  v9 = v6 >> 1;
  if ( v7 )
  {
    v12 = 0;
    v10 = v9 == 0;
    v11 = v9 < 0;
    if ( v9 > 0 )
    {
      v12 = __OFSUB__(8, v6 >> 1);
      v10 = v6 >> 1 == 8;
      v11 = 8 - (v6 >> 1) < 0;
    }
    if ( (unsigned __int8)(v11 ^ v12) | v10 )
    {
      a3 = 16;
      v13 = v5;
    }
    else
    {
      v13 = 0;
    }
    if ( (unsigned __int8)(v11 ^ v12) | v10 )
    {
LABEL_36:
      printf("uhoh");
    }
    else
    {
      do
      {
        v14 = (unsigned short *)(v5 + 2 * v13);
        v13 += 2;
        *(unsigned short *)result = *v14;
        v15 = (unsigned short *)(result + 2);
        *v15 = v14[1];
        result = (unsigned int)(v15 + 1);
      }
      while ( v13 < 8 );
    }
LABEL_38:
    result = *(unsigned int *)(v4 + 124) - 1;
    *(unsigned int *)(v4 + 124) = result;
    return result;
  }
  result = sub_239F08((unsigned __int8 *)v4, 3);
  v16 = (unsigned __int8)result;
  if ( (unsigned __int8)result == 7 )
  {
    result = 8 * sub_239F08((unsigned __int8 *)v4, 3) | 7;
    v16 = (unsigned __int8)result;
  }
  if ( v16 == 15 )
  {
    v53 = sub_239F08((unsigned __int8 *)v4, 13);
    result = sub_239F08((unsigned __int8 *)v4, 13);
    *v3 = v53;
    v3[1] = v53;
    v3[2] = result;
    v3[3] = v53;
    v3[4] = v53;
    v3[5] = result;
    v3[6] = v53;
    v3[7] = v53;
  }
  else if ( v16 > 15 )
  {
    if ( v16 == 47 )
    {
      v56 = *(unsigned short *)((compressionTableWat+0x90)+(2 * sub_239F08((unsigned __int8 *)v4, 5)));
      result = *(unsigned __int16 *)((compressionTableWat+0x90)+(2 * sub_239F08((unsigned __int8 *)v4, 5)));
      *v3 = v56;
      v3[1] = result;
      v3[2] = v56;
      v3[3] = v56;
      v3[4] = result;
      v3[5] = v56;
      v3[6] = v56;
      v3[7] = result;
    }
    else if ( v16 > 47 )
    {
      if ( v16 == 55 )
      {
        v57 = *(unsigned short *)((compressionTableWat+0x90)+(2 * sub_239F08((unsigned __int8 *)v4, 5)));
        result = *(unsigned __int16 *)((compressionTableWat+0x90)+(2 * sub_239F08((unsigned __int8 *)v4, 5)));
        *v3 = v57;
        v3[1] = result;
        v3[2] = result;
        v3[3] = v57;
        v3[4] = result;
        v3[5] = result;
        v3[6] = v57;
        v3[7] = result;
      }
      else if ( v16 == 63 )
      {
        v19 = *(unsigned short *)((compressionTableWat+0x90)+(2 * sub_239F08((unsigned __int8 *)v4, 5)));
        result = *(unsigned __int16 *)((compressionTableWat+0x90)+(2 * sub_239F08((unsigned __int8 *)v4, 5)));
        *v3 = v19;
        v3[1] = result;
        v3[2] = v19;
        v3[3] = result;
        v3[4] = v19;
        v3[5] = result;
        v3[6] = v19;
LABEL_26:
        v3[7] = result;
      }
    }
    else
    {
      switch ( v16 )
      {
        case 23:
          v54 = sub_239F08((unsigned __int8 *)v4, 13);
          result = sub_239F08((unsigned __int8 *)v4, 13);
          *v3 = v54;
          v3[1] = result;
          v3[2] = v54;
          v3[3] = v54;
          v3[4] = result;
          v3[5] = v54;
          LOWORD(v49) = result;
          v3[6] = v54;
LABEL_53:
          v3[7] = v49;
          break;
        case 31:
          v55 = sub_239F08((unsigned __int8 *)v4, 13);
          result = sub_239F08((unsigned __int8 *)v4, 13);
          *v3 = v55;
          v3[1] = result;
          v3[2] = result;
          v3[3] = v55;
          v3[4] = result;
          v3[5] = result;
          v3[6] = v55;
          v3[7] = result;
          break;
        case 39:
          v18 = *(unsigned short *)((compressionTableWat+0x90)+(2 * sub_239F08((unsigned __int8 *)v4, 5)));
          result = *(unsigned __int16 *)((compressionTableWat+0x90)+(2 * sub_239F08((unsigned __int8 *)v4, 5)));
          *v3 = v18;
          v3[1] = v18;
          v3[2] = result;
          v3[3] = v18;
          v3[4] = v18;
          v3[5] = result;
          v3[6] = v18;
          v3[7] = v18;
          break;
      }
    }
  }
  else if ( (unsigned int)v16 < 8 )
  {
	  printf("%x\n", v16);
    //v17 = (int)*(&off_186C2C + v16);
    switch ( v16 )
    {
      case 0:
        v20 = sub_239F08((unsigned __int8 *)v4, 5);
		printf("case 0\n");
        v21 = 4;
		printf("s");
		printf("%x\n", v4);
		printf("%x\n", v20);
        v22 = (2 * v20);
		printf("s");
        result = (unsigned int)(v3 - 1);
        do
        {
          --v21;
          *(unsigned short *)(result + 2) = v22;
          *(unsigned short *)(result + 4) = v22;
          result += 4;
        }
        while ( v21 );
        return result;
      case 1:
	    printf("case 1\n");
        result = sub_239F08((unsigned __int8 *)v4, 13);
        v31 = 4;
        v32 = (int)(v3 - 1);
        do
        {
          --v31;
          *(unsigned short *)(v32 + 2) = result;
          *(unsigned short *)(v32 + 4) = result;
          v32 += 4;
        }
        while ( v31 );
        return result;
      case 2:
	    //goto LABEL_26;
		printf("case 2\n");
	    v33 = (unsigned __int8)sub_239F08((unsigned __int8 *)v4, 5);
        v34 = *(_WORD *)((compressionTableWat+0x90)+(2 * v33));
		printf("v34: %x\n", v34);
		printf("12\n");
		v35 = __ROR4__(*(_DWORD *)((compressionTableWat)+(4 * v33)), 4);
        //v35 = /*__ROR4__(*/ *(_DWORD *)((compressionTableWat)+(4 * v33))/*, 4)*/;
		printf("v35: %x\n", v35);
        v36 = (aTable + ((unsigned __int8)v35));
		printf("v36: %x\n", v36);
        v35 >>= 8;
		printf("%x\n", v35);
        v37 = (aTable + ((unsigned __int8)v35));
        v35 >>= 8;
		printf("%x\n", v37);
        v38 = *v37;
		printf("%x\n", v35);
        v39 = 9 * *v36;
		printf("%x\n", v35);
        v40 = *(aTable + ((unsigned __int8)v35));
        v41 = *(aTable + (BYTE1(v35)));
        *v3 = v34;
        result = 9 * (9 * (v38 + v39) + v40) + v41; 
		/*if(v34 == 0x668)
			result = 0x1338;
		else if(v34 == 0x1338)
			result = 0x668;*/
		printf("result: %x\n", result);
		*v3 = v34;
        v3[1] = result;
        v3[2] = v34;
        v3[3] = result;
        v3[4] = v34;
        v3[5] = result;
        v3[6] = v34;
        goto LABEL_26;
      case 3:
	    //goto LABEL_53;
	    printf("case 3\n");
        result = sub_239F08((unsigned __int8 *)v4, 13);
		printf("%x\n",result);
        v42 = __ROR4__(*(_DWORD *)((compressionTableWat)+(4 * result)), 4);
        v43 = (unsigned __int8 *)(aTable + ((unsigned __int8)v42));
        v42 >>= 8;
        v44 = (unsigned __int8 *)(aTable + ((unsigned __int8)v42));
        v42 >>= 8;
        v45 = *v44;
        v46 = 9 * *v43;
        v47 = *(aTable + ((unsigned __int8)v42));
        v48 = *(aTable + (BYTE1(v42)));
		printf("%x\n",aTable + (BYTE1(v42)));
        *v3 = result;
        v49 = 9 * (9 * (v45 + v46) + v47) + v48; 
		//printf("%x %x %x %x \n", v45, v46, v47, v48);
		printf("%x\n",result);
		v49 = result / 3;
		/*if(result == 0x3c)
			v49 = 0x14;
		if(result == 0x222)
			v49 = 0xb6;
		if(result == 0x12fc)
			v49 = 0x654;*/
		//system("pause");
        v3[1] = v49;
        v3[2] = result;
        v3[3] = v49;
        v3[4] = result;
        v3[5] = v49;
        v3[6] = result;
        goto LABEL_53;
      case 4:
        v50 = (unsigned __int8)sub_239F08((unsigned __int8 *)v4, 8);
		printf("v4: %x\n", v4);
		printf("v50: %x\n", v50);
        v51 = 0;
        do
        {
          if ( v50 & (1 << v51) ){
			printf("aaa: %x\n", *((unsigned int *)(v4)));
			printf("aaa2: %x\n", *((unsigned int *)(v4+4)));
			printf("aaa3: %x\n", *((unsigned int *)(v4+8)));
			unsigned int * aaa3 = *((unsigned int *)(v4+8));
			printf("aaa3: %x\n", aaa3);
			printf("aaa5: %x\n", *((unsigned int *)(aaa3+1)));
			
			
			//printf("%x", sub_239F08((unsigned __int8 *)v4, 5));
            result = *(unsigned short *)((compressionTableWat+0x90)+(2 * (unsigned __int8)sub_239F08((unsigned __int8 *)v4, 5)));
			printf("a");
          }else{
            result = sub_239F08((unsigned __int8 *)v4, 13);
		  }
          ++v51;
		  //printf("s");
          *v3 = result;
          ++v3;
        }
        while ( v51 < 8 );
        return result;
      case 5:
	    printf("case 5\n");
        v23 = sub_239F08((unsigned __int8 *)v4, 5);
        v24 = v23 + 1;
        v10 = v23 == -1;
        result = (unsigned int)v3;
        v13 = v5;
        *(unsigned int *)(v4 + 124) = v24;
        if ( v10 )
          return result;
        v27 = 0;
        v25 = v9 == 0;
        v26 = v9 < 0;
        if ( v9 > 0 )
        {
		  //system("pause");
          v27 = __OFSUB__(8, v6 >> 1);
          v25 = v6 >> 1 == 8;
          v26 = 8 - (v6 >> 1) < 0;
        }
        if ( (unsigned __int8)(v26 ^ v27) | v25 )
        {
          a3 = 16;
          goto LABEL_36;
        }
        v28 = 0;
        do
        {
          v29 = (unsigned short *)(v5 + 2 * v28);
          v28 += 2;
          *(unsigned short *)result = *v29;
          v30 = (unsigned short *)(result + 2);
          *v30 = v29[1];
          result = (unsigned int)(v30 + 1);
        }
        while ( v28 < 8 );
        break;
      case 6:
	    printf("case 6\n");
        return result;
      case 7:
	    printf("case 7\n");
        v52 = sub_239F08((unsigned __int8 *)v4, 13);
        result = sub_239F08((unsigned __int8 *)v4, 13);
        *v3 = v52;
        v3[1] = result;
        v3[2] = v52;
        v3[3] = result;
        v3[4] = v52;
        v3[5] = result;
        v3[6] = v52;
        v3[7] = result;
        return result;
    }
    goto LABEL_38;
  }
  return result;
}

int main(){
	
	FILE* layer = fopen("layerA.bin", "rb");
	
	FILE* table = fopen("compTable2.bin", "rb");
	
	fread((compressionTableWat),1,0x20090,table);
	
	
	FILE* table2 = fopen("aTable.bin", "rb");
	
	fread((aTable),1,0x1000,table2);
	
	
	unsigned char* layerdata = malloc(0xffff);
	printf("%x\n", layerdata);
	
	fread(layerdata,1,0xffff,layer);
	
	unsigned int* layerinfo = malloc(0x100000/4);
	printf("%x\n", layerinfo);
	
	layerinfo[0] = 0x0;
	layerinfo[1] = layerdata;
	layerinfo[2] = layerdata;
	layerinfo[2] += 2;
	layerinfo[3] = 0;
	printf("%x %x %x %x\n", layerinfo[0], layerinfo[1], layerinfo[2], layerinfo[3]);
	
	unsigned char* out1 = layerinfo+(0x150/4);
	unsigned char* out2 = 0x14e7ddb0;
	printf("%x\n", layerinfo);
	printf("%x\n", out1);
	//system("pause");
	
	unsigned char* writeOut = out1;
	
	for(int i = 0; i < 0x4b0; i++){
		
		printf("return: %x\n", sub_186B7C(layerinfo,out1,out2));
		
		printf("aaa %x %x\n", (_WORD *)(writeOut), *(_WORD *)(writeOut+0x752));
		
		if(*(_WORD *)(writeOut+0x742) == 0x2f98){
			printf("%x\n",*(out1+(0xe)));
			system("pause");
		}
		
		system("pause");
		
		out1 += 0x10;
		out2 += 0x10;
		
		//layerinfo[3] = *(_WORD *)(layerinfo[2]-2);
		
		printf("%x %x %x\n", layerinfo[1],layerinfo[2], layerinfo[3]);
		if(layerinfo[3])
			//system("pause");
		
		printf("sss");
		
		FILE* layerO = fopen("layerOut.bin", "wb");
	
		fwrite(writeOut,1,0x9600,layerO);
	
		fclose(layerO);
		
	}
	
	
	FILE* layerO = fopen("layerOut.bin", "wb");
	
	fwrite(writeOut,1,0x9600,layerO);
	
	fclose(layerO);
	
}
