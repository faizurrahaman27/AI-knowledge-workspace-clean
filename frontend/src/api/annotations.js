import api from "./axios";

export async function createAnnotation(documentId, annotation) {
  return (await api.post(`/documents/${documentId}/annotations`, annotation)).data;
}
export async function listAnnotations(documentId) {
  return (await api.get(`/documents/${documentId}/annotations`)).data;
}
export async function deleteAnnotation(documentId, annotationId) {
  return (await api.delete(`/documents/${documentId}/annotations/${annotationId}`)).data;
}
