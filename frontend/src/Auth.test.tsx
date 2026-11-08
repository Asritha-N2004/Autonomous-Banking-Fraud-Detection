import {afterEach,describe,expect,it,vi} from 'vitest'
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import Auth from './Auth'
import {api} from './api'

vi.mock('./api',()=>({api:vi.fn()}))
afterEach(()=>{cleanup();vi.resetAllMocks()})

function openRegistration(){
    render(<Auth onLogin={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button',{name:'Create account'}))
}
function fill(password='Synthetic-Account-Password!',confirmation=password){
    fireEvent.change(screen.getByLabelText('Username'),{target:{value:'synthetic-analyst'}})
    fireEvent.change(screen.getByLabelText('Password',{exact:true}),{target:{value:password}})
    fireEvent.change(screen.getByLabelText('Confirm password'),{target:{value:confirmation}})
}
describe('Account creation',()=>{
    it('allows simple names and email addresses without a username pattern',()=>{
        openRegistration()
        const username=screen.getByLabelText('Username')
        expect(username).not.toHaveAttribute('pattern')
        expect(username).not.toHaveAttribute('minlength')
        fireEvent.change(username,{target:{value:'Synthetic Full Name'}})
        expect(username).toBeValid()
        fireEvent.change(username,{target:{value:'synthetic@example.test'}})
        expect(username).toBeValid()
    })
    it('switches between registration and sign-in',()=>{
        openRegistration();expect(screen.getByLabelText('Confirm password')).toBeInTheDocument()
        expect(screen.getByText('Analyst',{exact:true})).toBeInTheDocument()
        fireEvent.click(screen.getByRole('button',{name:'Sign in'}))
        expect(screen.queryByLabelText('Confirm password')).not.toBeInTheDocument()
        expect(screen.getByRole('button',{name:'Sign in to workspace'})).toBeInTheDocument()
    })
    it('checks password confirmation before making a request',()=>{
        openRegistration();fill('Synthetic-Account-Password!','Different-Account-Password!')
        fireEvent.click(screen.getByRole('button',{name:'Create account'}))
        expect(screen.getByRole('alert')).toHaveTextContent('Passwords do not match')
        expect(api).not.toHaveBeenCalled()
    })
    it('creates an account and enters the authenticated workspace',async()=>{
        const onLogin=vi.fn();const user={id:'synthetic-user',username:'synthetic-analyst',role:'ANALYST'}
        vi.mocked(api).mockResolvedValue({user})
        render(<Auth onLogin={onLogin}/>);fireEvent.click(screen.getByRole('button',{name:'Create account'}));fill()
        fireEvent.click(screen.getByRole('button',{name:'Create account'}))
        await waitFor(()=>expect(onLogin).toHaveBeenCalledWith(user))
        expect(api).toHaveBeenCalledWith('/auth/register',{username:'synthetic-analyst',password:'Synthetic-Account-Password!',confirm_password:'Synthetic-Account-Password!'})
    })
    it('shows duplicate-name errors and permits retry',async()=>{
        vi.mocked(api).mockRejectedValue(new Error('Username is already taken.'))
        openRegistration();fill();fireEvent.click(screen.getByRole('button',{name:'Create account'}))
        expect(await screen.findByRole('alert')).toHaveTextContent('Username is already taken')
        expect(screen.getByRole('button',{name:'Create account'})).toBeEnabled()
    })
})
