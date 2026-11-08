export async function api(path:string,body?:unknown,method?:string){
  const response=await fetch('/api'+path,{credentials:'include',method:method || (body?'POST':'GET'),headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined})
  if(!response.ok){let message='Request failed';try{const error=await response.json();message=typeof error.detail==='string'?error.detail:Array.isArray(error.detail)?error.detail.map((item:{msg:string})=>item.msg).join('; '):'Invalid request'}catch{}throw new Error(message)}
  return response.json()
}
export async function download(caseId:string,format:string){
  const response=await fetch(`/api/investigations/${caseId}/report?format=${format}`,{credentials:'include'})
  if(!response.ok)throw new Error('Export denied or failed')
  const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download=`investigation-${caseId}.${format}`;a.click();URL.revokeObjectURL(url)
}
