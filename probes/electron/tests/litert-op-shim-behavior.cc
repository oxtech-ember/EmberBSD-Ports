// SPDX-License-Identifier: Apache-2.0

#include <cstdio>
#include <cstring>
#include <vector>
#include "flatbuffers/flatbuffers.h"
#include "flatbuffers/flexbuffers.h"
#include "tensorflow/lite/mutable_op_resolver.h"
#include "tensorflow/lite/string_util.h"
#include "tensorflow_text/core/kernels/fast_bert_normalizer_model_generated.h"
#include "tensorflow_text/core/kernels/fast_wordpiece_tokenizer_model_generated.h"
extern "C" void AddFastBertNormalize(tflite::MutableOpResolver*);
extern "C" void AddFastWordpieceTokenize(tflite::MutableOpResolver*);
extern "C" void AddFastWordpieceDetokenize(tflite::MutableOpResolver*);
static void report(TfLiteContext*, const char*, ...) {}
static TfLiteStatus resize(TfLiteContext*, TfLiteTensor* t, TfLiteIntArray* d) {
 TfLiteIntArrayFree(t->dims); t->dims=d; size_t n=1; for(int i=0;i<d->size;i++) n*=d->data[i];
 if(t->type==kTfLiteInt64) return TfLiteTensorRealloc(n*sizeof(int64_t),t);
 return kTfLiteOk;
}
static TfLiteIntArray* dims(int n, int d) { auto* a=TfLiteIntArrayCreate(n);for(int i=0;i<n;i++) a->data[i]=d;return a; }
static bool run(const TfLiteRegistration* op, const std::vector<uint8_t>& model, bool wordpiece) {
 TfLiteTensor t[7]={}; t[0].type=kTfLiteString;t[0].allocation_type=kTfLiteDynamic;t[0].dims=dims(1,1);
 tflite::DynamicBuffer input;input.AddString("hello",5);input.WriteToTensor(&t[0],nullptr);
 t[1].type=kTfLiteUInt8;t[1].allocation_type=kTfLiteMmapRo;t[1].dims=dims(1,model.size());t[1].data.uint8=const_cast<uint8_t*>(model.data());t[1].bytes=model.size();
 int outs=wordpiece?5:3;for(int i=0;i<outs;i++){t[i+2].type=i==0?kTfLiteString:kTfLiteInt64;t[i+2].allocation_type=kTfLiteDynamic;}
 TfLiteContext ctx={};ctx.tensors=t;ctx.tensors_size=2+outs;ctx.ResizeTensor=resize;ctx.ReportError=report;
 TfLiteNode node={};node.inputs=TfLiteIntArrayCreate(2);node.inputs->data[0]=0;node.inputs->data[1]=1;node.outputs=TfLiteIntArrayCreate(outs);for(int i=0;i<outs;i++)node.outputs->data[i]=i+2;
 flexbuffers::Builder attrs;attrs.Map([&]{if(!wordpiece)attrs.Bool("get_offsets",true);});attrs.Finish();const auto& a=attrs.GetBuffer();node.user_data=op->init(&ctx,(const char*)a.data(),a.size());
 bool ok=op->prepare(&ctx,&node)==kTfLiteOk && op->invoke(&ctx,&node)==kTfLiteOk;
 if(ok){auto str=tflite::GetString(&t[2],0); if(wordpiece){ok=std::string(str.str,str.len)=="[UNK]" && t[3].data.i64[0]==7 && t[4].data.i64[0]==0 && t[4].data.i64[1]==1 && t[5].data.i64[0]==0 && t[6].data.i64[0]==5;} else {ok=std::string(str.str,str.len)=="hello" && t[3].data.i64[0]==0 && t[3].data.i64[5]==5 && t[4].data.i64[0]==0 && t[4].data.i64[1]==6;}}
 // The same registered callback must reject a rank-two input during Prepare.
 TfLiteIntArrayFree(t[0].dims);t[0].dims=dims(2,1);ok=ok && op->prepare(&ctx,&node)==kTfLiteError;
 op->free(&ctx,node.user_data);TfLiteIntArrayFree(node.inputs);TfLiteIntArrayFree(node.outputs);
 for(int i=0;i<2+outs;i++){if(i==1){TfLiteIntArrayFree(t[i].dims);continue;}TfLiteTensorFree(&t[i]);}
 return ok;
}
int main(){
 tflite::MutableOpResolver r;AddFastBertNormalize(&r);AddFastWordpieceTokenize(&r);AddFastWordpieceDetokenize(&r);
 auto* bert=r.FindOp("FastBertNormalize",1);auto* wp=r.FindOp("FastWordpieceTokenizeWithOffsets",1);auto* detok=r.FindOp("TFText>FastWordpieceDetokenize",1);
 if(!bert||!wp||!detok||!detok->invoke)return 1;
 flatbuffers::FlatBufferBuilder a; auto trie=a.CreateVector(std::vector<uint32_t>(256));auto pool=a.CreateVector(std::vector<uint8_t>{0}); auto am=tensorflow::text::CreateFastBertNormalizerModel(a,false,trie,0,pool);a.Finish(am);std::vector<uint8_t> amodel(a.GetBufferPointer(),a.GetBufferPointer()+a.GetSize());
 flatbuffers::FlatBufferBuilder b;auto trie2=b.CreateVector(std::vector<uint32_t>(256));auto suffix=b.CreateString("##");auto unk=b.CreateString("[UNK]");auto bm=tensorflow::text::CreateFastWordpieceTokenizerConfig(b,trie2,0,0,0,1,suffix,unk,7);b.Finish(bm);std::vector<uint8_t> bmodel(b.GetBufferPointer(),b.GetBufferPointer()+b.GetSize());
 if(!run(bert,amodel,false)||!run(wp,bmodel,true))return 2;
 std::puts("PASS: registered BERT normalization and WordPiece token/offset outputs; invalid rank rejected");return 0;
}
