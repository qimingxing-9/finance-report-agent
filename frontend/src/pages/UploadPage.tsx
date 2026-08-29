import FileUpload from '../components/FileUpload'

export default function UploadPage() {
  return (
    <div>
      <h2 className="text-lg font-medium text-gray-800 mb-6">上传财报 PDF</h2>
      <FileUpload />
    </div>
  )
}
