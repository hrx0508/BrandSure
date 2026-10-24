import { createBrowserRouter } from 'react-router-dom'
import AppShell from '../components/layout/AppShell.jsx'
import Login from '../features/auth/Login.jsx'
import Home from '../features/home/Home.jsx'
import Insights from '../features/insights/Insights.jsx'
import Team from '../features/team/Team.jsx'
import Guide from '../features/guide/Guide.jsx'
import Settings from '../features/settings/Settings.jsx'
import PostsList from '../features/posts/PostsList.jsx'
import NewPost from '../features/posts/NewPost.jsx'
import PostPage from '../features/posts/PostPage.jsx'
import BrandKits from '../features/brand-kits/BrandKits.jsx'
import BrandKitDetail from '../features/brand-kits/BrandKitDetail.jsx'

export const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  {
    path: '/', element: <AppShell />,
    children: [
      { index: true, element: <Home /> },
      { path: 'brand-kits', element: <BrandKits /> },
      { path: 'brand-kits/:id', element: <BrandKitDetail /> },
      { path: 'posts', element: <PostsList /> },
      { path: 'posts/new', element: <NewPost /> },
      { path: 'posts/:id', element: <PostPage /> },
      { path: 'insights', element: <Insights /> },
      { path: 'team', element: <Team /> },
      { path: 'guide', element: <Guide /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
])
