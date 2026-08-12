import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/login.vue'),
    },
    {
      path: '/',
      component: () => import('../layouts/AppShell.vue'),
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('../views/Home.vue'),
        },
        {
          path: 'clients',
          name: 'clients',
          component: () => import('../views/Clients.vue'),
        },
        {
          path: 'missions',
          name: 'missions',
          component: () => import('../views/Missions.vue'),
        },
      ],
    },
    {
      path: '/profil',
      name: 'profile',
      component: () => import('../views/Profile.vue'),
    },
  ],
})

router.beforeEach((to) => {
  const isAuthenticated = !!localStorage.getItem('access_token')

  if (to.name !== 'login' && !isAuthenticated) {
    return { name: 'login' }
  }
  if (to.name === 'login' && isAuthenticated) {
    return { name: 'home' }
  }
})

export default router
