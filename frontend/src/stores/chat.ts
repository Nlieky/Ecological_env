import { computed, markRaw, reactive, ref } from 'vue'
import { defineStore } from 'pinia'
import { conversationsService } from '@/api/modules/conversations'
import { queryService } from '@/api/modules/query'
import { useActionStore } from './action'
import type { ConversationListItem, ConversationDetail, SessionTrace } from '@/api/types/api.types'

export interface ChatMessage {
  id: string; role: 'user'|'assistant'; content: string; timestamp: string
  trace?: SessionTrace|null; streaming?: boolean; progress?: string; error?: string
  elapsedMs?: number; queueElapsedMs?: number; turnElapsedMs?: number
  stageDurations?: { subagent:string; elapsedMs:number }[]
  chartData?: { charts:any[] }|null; channel?: 'action'|'chat'
}
export type ConversationRunStatus='idle'|'queued'|'running'|'completed'|'failed'|'cancelled'
interface Runtime { messages:ChatMessage[]; status:ConversationRunStatus; error:string|null; hydrated:boolean; controller?:AbortController; settle?:()=>void }
let seq=0
const nextId=()=> 'm'+Date.now()+'_'+(++seq)
const labels:Record<string,string>={'multi-dimensional-data-perception':'数据感知','anomaly-detection':'异常检测','rule-reasoning':'规则推理','disposition-execution':'研判处置'}

export const useChatStore=defineStore('chat',()=>{
  const conversations=ref<ConversationListItem[]>([])
  const current=ref<ConversationDetail|null>(null)
  const sessionId=ref<string>()
  const runtimes=reactive(new Map<string,Runtime>())
  const draft=reactive<ChatMessage[]>([])
  const navigating=ref(false),creating=ref(false)
  let navGeneration=0
  const runtime=computed(()=>sessionId.value?runtimes.get(sessionId.value):undefined)
  const messages=computed(()=>runtime.value?.messages||draft)
  const loading=computed(()=>navigating.value||creating.value||['queued','running'].includes(runtime.value?.status||''))
  const error=computed(()=>runtime.value?.error||null)
  function ensure(id:string){let r=runtimes.get(id);if(!r){r=reactive({messages:id==='__draft__'?draft:[],status:'idle',error:null,hydrated:id==='__draft__'}) as Runtime;runtimes.set(id,r)}return r}
  function conversationStatus(id:string):ConversationRunStatus{return runtimes.get(id)?.status||'idle'}
  function cancelConversation(id:string){const r=runtimes.get(id);if(!r)return;r.controller?.abort();r.settle?.();r.controller=undefined;r.settle=undefined;if(['queued','running'].includes(r.status))r.status='cancelled'}
  function cancelReception(){if(sessionId.value)cancelConversation(sessionId.value)}
  async function fetchConversations(page=1){try{const x=await conversationsService.list(page);conversations.value=x.data.conversations}catch{}}
  function history(d:ConversationDetail){return(d.messages||[]).filter(m=>m.role==='user'||m.role==='assistant').map(m=>{const x:ChatMessage={id:nextId(),role:m.role as any,content:m.content||'',timestamp:m.timestamp||new Date().toISOString()};const c=m.tool_call_info?.chartData;if(c)x.chartData=Array.isArray(c)?{charts:c}:c.charts?c:{charts:[]};return x})}
  async function openConversation(id:string){
    const token=++navGeneration
    creating.value=false
    const r=ensure(id)
    if(r.hydrated){sessionId.value=id;return}
    navigating.value=true
    try{const x=await conversationsService.detail(id);if(token!==navGeneration)return;sessionId.value=id;current.value=x.data;if(!r.messages.length)r.messages.push(...history(x.data));r.hydrated=true}
    catch{}finally{if(token===navGeneration)navigating.value=false}
  }
  async function sendQuery(query:string,mode:'chat'|'floating'='chat'){
    const activeId=sessionId.value,id=activeId||'__draft__',q=query.trim()
    if(!q||creating.value)return
    const r=ensure(id)
    if(['queued','running'].includes(r.status))return
    r.status='running';r.error=null
    const started=performance.now(),channel=mode==='floating'?'action':'chat'
    r.messages.push({id:nextId(),role:'user',content:q,timestamp:new Date().toISOString(),channel})
    const aid=nextId()
    r.messages.push({id:aid,role:'assistant',content:'',timestamp:new Date().toISOString(),streaming:true,progress:'等待处理…',channel})
    let terminal=false
    const alive=()=>!terminal&&runtimes.get(id)===r&&conversationStatus(id)!=='cancelled'
    const patch=(p:Partial<ChatMessage>)=>{if(!alive())return;const m=r.messages.find(x=>x.id===aid);if(m)Object.assign(m,p)}
    const calls:{key:string;name:string;summary?:string}[]=[],starts=new Map<string,number[]>(),durations:{subagent:string;elapsedMs:number}[]=[],charts:any[]=[]
    const vc=useActionStore().viewContext,viewCtx=vc&&Object.keys(vc).length?JSON.stringify(vc):''
    try{await new Promise<void>((resolve,reject)=>{
      const fail=(msg:string)=>{if(!alive())return;patch({error:msg,streaming:false,progress:'',elapsedMs:performance.now()-started,stageDurations:[...durations],chartData:charts.length?{charts}:null});terminal=true;r.status='failed';r.error=msg;reject(new Error(msg))}
      r.settle=()=>fail('已停止接收；服务器任务可能仍在运行')
      r.controller=markRaw(queryService.executeStream({query:q,session_id:activeId,view_context:viewCtx,...(mode==='floating'?{mode:'action'}:{})},{
        onProgress:e=>{if(!alive())return;const name=labels[e.subagent]||e.subagent;if(e.stage==='start'){const a=starts.get(e.subagent)||[];a.push(performance.now());starts.set(e.subagent,a)}else if(e.stage==='done'){const s=starts.get(e.subagent)?.shift();durations.push({subagent:name,elapsedMs:Number.isFinite(e.elapsed_ms)?Math.max(0,e.elapsed_ms!):s==null?0:performance.now()-s});calls.push({key:e.subagent,name,summary:e.summary});if(e.chartData)charts.push(...(Array.isArray(e.chartData)?e.chartData:e.chartData.charts||[e.chartData]))}patch({progress:e.stage==='start'?'正在调用「'+name+'」子智能体…':'「'+name+'」完成'})},
        onAction:a=>{if(alive()&&a)useActionStore().dispatch(a)},
        onDelta:t=>{const m=r.messages.find(x=>x.id===aid);patch({content:(m?.content||'')+t})},
        onDone:(content,sid,timing)=>{if(!alive())return;const m=r.messages.find(x=>x.id===aid);if(m)Object.assign(m,{content:content||'(空回答)',streaming:false,progress:'',elapsedMs:performance.now()-started,...timing,stageDurations:[...durations],chartData:charts.length?{charts}:null});if(m&&calls.length)m.trace={session_id:sid||id,api_call:null,master_decision:{decision_path:calls.map(c=>c.name)},subagent_executions:calls.map(c=>({subagent_name:c.key,status:'completed',result_summary:c.summary||''})),operator_calls:[],llm_calls:[]};terminal=true;r.status='completed';void fetchConversations();resolve()},
        onError:fail
      }))
    })}catch(e:any){if(conversationStatus(id)!=='cancelled')r.error=e?.message||'查询失败'}finally{r.controller=undefined;r.settle=undefined}
  }
  function clearMessages(){++navGeneration;navigating.value=false;creating.value=false;for(const id of [...runtimes.keys()])cancelConversation(id);runtimes.clear();sessionId.value=undefined;current.value=null;draft.splice(0)}
  async function startNewConversation(){const token=++navGeneration;creating.value=true;navigating.value=false;sessionId.value=undefined;current.value=null;draft.splice(0);try{const x:any=await conversationsService.create('新对话');if(token!==navGeneration)return;const id=(x.data??x)?.id;if(id){sessionId.value=id;ensure(id).hydrated=true}await fetchConversations()}catch{if(token===navGeneration)sessionId.value=undefined}finally{if(token===navGeneration)creating.value=false}}
  return{conversations,current,messages,sessionId,loading,error,runtimes,fetchConversations,openConversation,sendQuery,clearMessages,startNewConversation,cancelReception,cancelConversation,conversationStatus}
})
