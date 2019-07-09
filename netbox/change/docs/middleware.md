# The Change Middleware

The change middleware is responsible for a couple of things related to changes.
Let’s start with a TL;DR bullet point overview:

- If we are in a change we check whether it’s still active and install the hooks
  that record the changes.
- If someone else is in a change, we give the user a message and disable all
  buttons that change something.
- Otherwise we don’t do anything.

Either of the first points is fairly complex on its own and deals with a couple
of different things at once. Let’s go through the source code of the function
together, and find out what exactly!

```python
if request.path.startswith('/admin'):
    return self.get_response(request)

in_change = request.session.get('in_change', False)
to_uninstall = []
if in_change:
```

We’re starting out by checking whether our user does admin-y things. If they do,
we put them on the fast track and ignore them.

We also need to set up a list of hooks we need to uninstall (called
`to_uninstall` here). It’s initially empty, but depending on where we will go
during our little voyage, it might get filled with hooks that need to be
uninstalled.

## Chapert I: We are in a change

If we ourselves are inside a change, we should first get the change set we are
working with. We have to take some precautions, because someone might have
deleted the change set while it’s still active.

```python
c = None
try:
    c = ChangeSet.objects.get(pk=request.session['change_id'])
except ChangeSet.DoesNotExist:
    messages.warning(request, "Your change session was deleted.")
    request.session['in_change'] = False
```

Then we check whether the change set is current. There is a utility function
defined on the change set called `in_use` that checks whether the last update on
the changeset was conducted before the timeout threshold.

```python
if c and c.in_use():
```

So, what should we do if the change is still in use? As it turns out, a couple
of things. First we install the save hooks that will record the changes made
during this request. There is one exception to that rule, however: if we are
currently trying to end this change during this request, we will not install
these hooks, because we would otherwise record the rollback as well, and we do
not want that.

```python
if request.path != '/change/toggle/':
    to_uninstall = install_save_hooks(request)
```

Alright, then are we done here? Not quite. We will also have to check whether
we have filled out the form that starts off a change yet! If the user did not,
we will redirect them to the form. One exception to that rule is if the change
ends, which means that they effectively cancelled the change.

```python
wrong_url = request.path not in ['/change/form/',
                                 '/change/toggle/']
if not request.session.get('change_information') and wrong_url:
    return redirect('/change/form')
```

Now we are done, and can take care of the other alternative, which is that our
change timed out.

```python
elif c:
```

If it timed out, we will simply unset the cookie that tells us that the user is
currently in a change, and give the user a visible message that tells them that
their session has timed out.

```python
messages.warning(request, "Your change session timed out.")
request.session['in_change'] = False
```

That is all we need to do if we are in a change.

## Chapter II: We are not in a change, but someone else might be

We are not in a change, so what do we have to do?

```python
else:
```

First, we see if there are any active changes. We also need to set that as a
cookie, so that the frontend’s editing capabilities can be disabled.

```python
cs = ChangeSet.objects.filter(active=True)
request.session['foreign_change'] = cs.exists()
```

Now, let’s check whether there is someone making a change. If not, we are done,
so we do not need an `else` clause this time—phew.

```python
if cs.exists() and cs.first().id != request.session.get('change_id'):
```

First, we get the change that is active.

```python
c = cs.first()
```

Secondly, we need to check whether that change is actually still active—the user
might have left without finalizing their change after all.

```
if c.in_use():
```

If the change really is currently active, we will leave the user with a message
and, if they attempted to do an edit of some sort, redirect them to where they
came from instead.

```python
message = "User {} is currently making a change."
messages.warning(request, message.format(c.user.username))
if any(request.path.endswith(s) for s in SITE_BLACKLIST):
    return redirect_to_referer(request)
```

What, however, if the changeset is not active anymore?

```python
else:
```

Well, helpful citizens as we are, we should mark this change as not active, revert it, and
save that result to the database, so let’s do just that!

```python
c.active = False
c.revert()
c.save()
```

If we are not in a change, we’ll have to do another thing: we’ll have to check whether we
are allowed to edit anything outside a change. If not, we’ll have to disallow doing that.
To that end, we look for the setting `NEED_CHANGE_FOR_WRITE`, and if this is set, we’ll
redirect the person who tries to edit anything.

```
if settings.NEED_CHANGE_FOR_WRITE:
    # dont check for change/toggle
    if any(request.path.endswith(s) for s in SITE_BLACKLIST[:-1]):
        return redirect_to_referer(request)
```

## Epilogue

Once we are done handling the change, we can now finally process the request.
As this is a middleware, we are not concerned with how the actual handler works,
and we simple demand to get a response.

```python
response = self.get_response(request)
```

But there is one more thing left for us to do: uninstall the signal handlers.
So let’s do just that:

```python
for handler in to_uninstall:
    handler['signal'].disconnect(handler['handler'],
                                 dispatch_uid='chgfield')
```

And now, after this tumultuous, arduous ride, we are finally able to return the
response:

```python
return response
```
