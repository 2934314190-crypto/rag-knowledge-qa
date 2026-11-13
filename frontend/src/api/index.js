import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

export function getHealth() {
  return http.get('/health')
}

export function uploadDocument(file, sourceName) {
  const formData = new FormData()
  formData.append('file', file)
  if (sourceName) formData.append('source_name', sourceName)
  return http.post('/documents/upload', formData)
}

export function getDocument(documentId) {
  return http.get(`/documents/${documentId}`)
}

export function updateMetadata(documentId, metadata) {
  return http.patch(`/documents/${documentId}/metadata`, { metadata })
}

export function sendChat(query, topK, threshold) {
  return http.post('/chat', { query, top_k: topK, threshold })
}

export default http