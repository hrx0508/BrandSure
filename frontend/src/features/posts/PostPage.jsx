import { useParams } from 'react-router-dom'
import { useAuth } from '../../lib/auth.jsx'
import AdminPost from './AdminPost.jsx'
import CreatorPost from './CreatorPost.jsx'
import ReviewerPost from './ReviewerPost.jsx'

/** Each role gets its own screen, so nobody sees another role's tools. */
export default function PostPage() {
  const { id } = useParams()
  const { user } = useAuth()
  if (user.role === 'creator') return <CreatorPost key={id} id={id} />
  if (user.role === 'reviewer') return <ReviewerPost key={id} id={id} />
  return <AdminPost key={id} id={id} />
}
