class KbfsWatcher(object):
    def __init__(self, path):
        self.path = path
        self.old_dir_listing = dict()
        print("KbfsWatcher watching %s" % self.path)
        self.thread = None
        self.not_stopped = True

    def check_dir(self):
        print("Entered check_dir")
        print(self.not_stopped)
        while self.not_stopped:
            new_dir_listing = {}

            fnames = os.listdir(self.path)
            fnames = [x for x in fnames if x.endswith('.sent')]

            for fname in fnames:
                new_dir_listing[fname] = os.path.getsize(
                        os.path.join(self.path, fname))
                if fname not in self.old_dir_listing:
                    self.on_created(fname)
                elif new_dir_listing[fname] != self.old_dir_listing[fname]:
                    self.on_modified(fname)

            for fname in self.old_dir_listing:
                if fname not in new_dir_listing:
                    self.on_deleted(fname)

            self.old_dir_listing = new_dir_listing
        
    def on_modified(self, fname):
        print("File %s modified" % fname)

    def on_created(self, fname):
        print("File %s created" % fname)

    def on_deleted(self, fname):
        print("File %s deleted" % fname)

    def start(self):
        self.thread = thrd.Thread(
                target=self.check_dir,
                args=tuple())
        self.thread.start()

    def stop(self):
        self.not_stopped = False
        self.thread.join()
        print("Stopping KbfsWatcher for %s" % self.path)


